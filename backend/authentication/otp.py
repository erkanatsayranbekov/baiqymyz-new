import hashlib
import hmac
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils.crypto import constant_time_compare
from django.utils import timezone
from rest_framework.authtoken.models import Token

from .models import CustomUser, OTPChallenge
from .mobizon import MobizonClient, MobizonError, mask_phone, sanitize_mobizon_data

logger = logging.getLogger(__name__)


class OTPError(Exception):
    pass


class OTPDisabledError(OTPError):
    pass


class OTPRateLimitedError(OTPError):
    pass


class OTPDeliveryError(OTPError):
    pass


class OTPVerificationError(OTPError):
    pass


def get_client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def build_vote_cookie(phone):
    raw = f'{phone}.{settings.SECRET_KEY}'
    return hashlib.sha256(raw.encode()).hexdigest()


class OTPService:
    def __init__(self, mobizon_client=None):
        self.mobizon_client = mobizon_client or MobizonClient()

    def request_otp(self, phone, request):
        if not settings.OTP_AUTH_ENABLED:
            raise OTPDisabledError('OTP authentication is disabled.')

        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        self._enforce_rate_limits(phone, ip_address)

        code = self.generate_otp(phone)
        now = timezone.now()
        challenge = OTPChallenge.objects.create(
            phone=phone,
            otp_hash=make_password(code),
            purpose=settings.OTP_PURPOSE_LOGIN,
            status=OTPChallenge.STATUS_PENDING,
            max_attempts=settings.OTP_MAX_ATTEMPTS,
            expires_at=now + timedelta(seconds=settings.OTP_TTL_SECONDS),
            ip_address=ip_address,
            user_agent=user_agent[:2000],
        )

        try:
            result = self.mobizon_client.send_sms(phone, self._build_sms_text(code))
        except MobizonError as exc:
            challenge.status = OTPChallenge.STATUS_FAILED
            challenge.metadata = {
                'mobizon_code': exc.code,
                'error': str(exc),
                'mobizon_data': sanitize_mobizon_data(exc.data),
            }
            challenge.save(update_fields=['status', 'metadata', 'updated_at'])
            logger.warning('OTP delivery failed for %s challenge=%s', mask_phone(phone), challenge.id)
            raise OTPDeliveryError('OTP delivery failed.') from exc

        challenge.status = OTPChallenge.STATUS_SENT
        challenge.sent_at = timezone.now()
        if isinstance(result, dict) and result.get('messageId'):
            challenge.mobizon_message_id = str(result['messageId'])
        challenge.metadata = {'mobizon_status': 'accepted'}
        challenge.save(update_fields=['status', 'sent_at', 'mobizon_message_id', 'metadata', 'updated_at'])
        logger.info('OTP sent for %s challenge=%s', mask_phone(phone), challenge.id)
        return challenge

    def verify_otp(self, phone, code):
        if not settings.OTP_AUTH_ENABLED:
            raise OTPDisabledError('OTP authentication is disabled.')

        now = timezone.now()
        verification_failed = False

        with transaction.atomic():
            challenge = (
                OTPChallenge.objects.select_for_update()
                .filter(
                    phone=phone,
                    purpose=settings.OTP_PURPOSE_LOGIN,
                    status__in=[OTPChallenge.STATUS_SENT, OTPChallenge.STATUS_LOCKED],
                    expires_at__gt=now,
                )
                .order_by('-created_at')
                .first()
            )

            if not challenge:
                raise OTPVerificationError('Invalid or expired OTP.')

            if challenge.locked_until and challenge.locked_until > now:
                raise OTPVerificationError('Invalid or expired OTP.')

            if challenge.status == OTPChallenge.STATUS_LOCKED:
                challenge.status = OTPChallenge.STATUS_SENT
                challenge.attempt_count = 0
                challenge.locked_until = None
                challenge.save(update_fields=['status', 'attempt_count', 'locked_until', 'updated_at'])

            if challenge.attempt_count >= challenge.max_attempts:
                challenge.status = OTPChallenge.STATUS_LOCKED
                challenge.locked_until = now + timedelta(seconds=settings.OTP_LOCKOUT_SECONDS)
                challenge.save(update_fields=['status', 'locked_until', 'updated_at'])
                verification_failed = True
            elif not self.verify_deterministic_otp(phone, code):
                challenge.attempt_count += 1
                challenge.last_attempt_at = now
                update_fields = ['attempt_count', 'last_attempt_at', 'updated_at']
                if challenge.attempt_count >= challenge.max_attempts:
                    challenge.status = OTPChallenge.STATUS_LOCKED
                    challenge.locked_until = now + timedelta(seconds=settings.OTP_LOCKOUT_SECONDS)
                    update_fields.append('status')
                    update_fields.append('locked_until')
                challenge.save(update_fields=update_fields)
                verification_failed = True
            else:
                challenge.status = OTPChallenge.STATUS_VERIFIED
                challenge.verified_at = now
                challenge.save(update_fields=['status', 'verified_at', 'updated_at'])

                user = self._get_or_create_auth_user(phone)
                self._ensure_legacy_user(phone)
                token, _ = Token.objects.get_or_create(user=user)
                return token, user, challenge

        if verification_failed:
            raise OTPVerificationError('Invalid or expired OTP.')

        raise OTPVerificationError('Invalid or expired OTP.')

    def create_manager_challenge(self, phone, request):
        if not settings.OTP_AUTH_ENABLED:
            raise OTPDisabledError('OTP authentication is disabled.')

        code = self.generate_otp(phone)
        now = timezone.now()
        return OTPChallenge.objects.create(
            phone=phone,
            otp_hash=make_password(code),
            purpose=settings.OTP_PURPOSE_LOGIN,
            status=OTPChallenge.STATUS_SENT,
            max_attempts=settings.OTP_MAX_ATTEMPTS,
            expires_at=now + timedelta(seconds=settings.OTP_TTL_SECONDS),
            sent_at=now,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:2000],
            metadata={'source': 'manager'},
        )

    def request_manager_login_otp(self, phone, user, request):
        if not settings.OTP_AUTH_ENABLED:
            raise OTPDisabledError('OTP authentication is disabled.')

        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        self._enforce_rate_limits(phone, ip_address)

        code = self.generate_otp(phone)
        ticket = secrets.token_urlsafe(32)
        now = timezone.now()
        challenge = OTPChallenge.objects.create(
            phone=phone,
            otp_hash=make_password(code),
            purpose=settings.OTP_PURPOSE_MANAGER_LOGIN,
            status=OTPChallenge.STATUS_PENDING,
            max_attempts=settings.OTP_MAX_ATTEMPTS,
            expires_at=now + timedelta(seconds=settings.OTP_TTL_SECONDS),
            ip_address=ip_address,
            user_agent=user_agent[:2000],
            metadata={
                'source': 'manager_login',
                'manager_user_id': user.id,
                'ticket_hash': make_password(ticket),
            },
        )

        try:
            result = self.mobizon_client.send_sms(phone, self._build_sms_text(code))
        except MobizonError as exc:
            challenge.status = OTPChallenge.STATUS_FAILED
            challenge.metadata = {
                **challenge.metadata,
                'mobizon_code': exc.code,
                'error': str(exc),
                'mobizon_data': sanitize_mobizon_data(exc.data),
            }
            challenge.save(update_fields=['status', 'metadata', 'updated_at'])
            logger.warning('Manager login OTP delivery failed for %s challenge=%s', mask_phone(phone), challenge.id)
            raise OTPDeliveryError('OTP delivery failed.') from exc

        challenge.status = OTPChallenge.STATUS_SENT
        challenge.sent_at = timezone.now()
        if isinstance(result, dict) and result.get('messageId'):
            challenge.mobizon_message_id = str(result['messageId'])
        challenge.metadata = {**challenge.metadata, 'mobizon_status': 'accepted'}
        challenge.save(update_fields=['status', 'sent_at', 'mobizon_message_id', 'metadata', 'updated_at'])
        logger.info('Manager login OTP sent for %s challenge=%s', mask_phone(phone), challenge.id)
        return ticket, challenge

    def verify_manager_login_otp(self, phone, ticket, code):
        if not settings.OTP_AUTH_ENABLED:
            raise OTPDisabledError('OTP authentication is disabled.')

        now = timezone.now()
        verification_failed = False

        with transaction.atomic():
            challenge = (
                OTPChallenge.objects.select_for_update()
                .filter(
                    phone=phone,
                    purpose=settings.OTP_PURPOSE_MANAGER_LOGIN,
                    status__in=[OTPChallenge.STATUS_SENT, OTPChallenge.STATUS_LOCKED],
                    expires_at__gt=now,
                )
                .order_by('-created_at')
                .first()
            )

            if not challenge:
                raise OTPVerificationError('Invalid or expired OTP.')

            if challenge.locked_until and challenge.locked_until > now:
                raise OTPVerificationError('Invalid or expired OTP.')

            if challenge.status == OTPChallenge.STATUS_LOCKED:
                challenge.status = OTPChallenge.STATUS_SENT
                challenge.attempt_count = 0
                challenge.locked_until = None
                challenge.save(update_fields=['status', 'attempt_count', 'locked_until', 'updated_at'])

            ticket_hash = challenge.metadata.get('ticket_hash', '')
            ticket_matches = bool(ticket_hash and check_password(ticket, ticket_hash))
            otp_matches = self.verify_deterministic_otp(phone, code)

            if challenge.attempt_count >= challenge.max_attempts:
                challenge.status = OTPChallenge.STATUS_LOCKED
                challenge.locked_until = now + timedelta(seconds=settings.OTP_LOCKOUT_SECONDS)
                challenge.save(update_fields=['status', 'locked_until', 'updated_at'])
                verification_failed = True
            elif not ticket_matches or not otp_matches:
                challenge.attempt_count += 1
                challenge.last_attempt_at = now
                update_fields = ['attempt_count', 'last_attempt_at', 'updated_at']
                if challenge.attempt_count >= challenge.max_attempts:
                    challenge.status = OTPChallenge.STATUS_LOCKED
                    challenge.locked_until = now + timedelta(seconds=settings.OTP_LOCKOUT_SECONDS)
                    update_fields.append('status')
                    update_fields.append('locked_until')
                challenge.save(update_fields=update_fields)
                verification_failed = True
            else:
                challenge.status = OTPChallenge.STATUS_VERIFIED
                challenge.verified_at = now
                challenge.save(update_fields=['status', 'verified_at', 'updated_at'])
                return challenge

        if verification_failed:
            raise OTPVerificationError('Invalid or expired OTP.')

        raise OTPVerificationError('Invalid or expired OTP.')

    def expire_old_challenges(self):
        now = timezone.now()
        expired_count = OTPChallenge.objects.filter(
            status__in=[OTPChallenge.STATUS_PENDING, OTPChallenge.STATUS_SENT, OTPChallenge.STATUS_LOCKED],
            expires_at__lte=now,
        ).update(status=OTPChallenge.STATUS_EXPIRED, updated_at=now)

        retention_cutoff = now - timedelta(days=settings.OTP_CHALLENGE_RETENTION_DAYS)
        deleted_count, _ = OTPChallenge.objects.filter(
            status__in=[
                OTPChallenge.STATUS_VERIFIED,
                OTPChallenge.STATUS_EXPIRED,
                OTPChallenge.STATUS_FAILED,
                OTPChallenge.STATUS_LOCKED,
            ],
            updated_at__lt=retention_cutoff,
        ).delete()

        return expired_count, deleted_count

    def generate_otp(self, phone):
        secret = self._get_otp_secret()
        digest = hmac.new(secret, phone.encode('utf-8'), hashlib.sha256).digest()
        upper_bound = 10 ** settings.OTP_CODE_LENGTH
        code_number = int.from_bytes(digest[:8], 'big') % upper_bound
        return str(code_number).zfill(settings.OTP_CODE_LENGTH)

    def verify_deterministic_otp(self, phone, code):
        return constant_time_compare(self.generate_otp(phone), code)

    def _get_otp_secret(self):
        if not settings.OTP_SECRET:
            raise ImproperlyConfigured('OTP_SECRET must be configured.')
        return settings.OTP_SECRET.encode('utf-8')

    def _build_sms_text(self, code):
        return f'Baiqymyz verification code: {code}'

    def _enforce_rate_limits(self, phone, ip_address):
        now = timezone.now()
        cooldown_start = now - timedelta(seconds=settings.OTP_RESEND_COOLDOWN_SECONDS)
        daily_start = now - timedelta(days=1)

        if OTPChallenge.objects.filter(phone=phone, created_at__gte=cooldown_start).exists():
            raise OTPRateLimitedError('Please wait before requesting another OTP.')

        phone_count = OTPChallenge.objects.filter(phone=phone, created_at__gte=daily_start).count()
        if phone_count >= settings.OTP_PHONE_DAILY_LIMIT:
            raise OTPRateLimitedError('OTP request limit exceeded.')

        if ip_address:
            ip_count = OTPChallenge.objects.filter(ip_address=ip_address, created_at__gte=daily_start).count()
            if ip_count >= settings.OTP_IP_DAILY_LIMIT:
                raise OTPRateLimitedError('OTP request limit exceeded.')

    def _get_or_create_auth_user(self, phone):
        User = get_user_model()
        user, created = User.objects.get_or_create(username=phone)
        if created:
            user.set_unusable_password()
            user.save(update_fields=['password'])
        return user

    def _ensure_legacy_user(self, phone):
        CustomUser.objects.get_or_create(
            phone_number=phone,
            defaults={'password': make_password(None)},
        )
