import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .models import (
    AuthAuditLog,
    CustomUser,
    DeviceFingerprintBinding,
    DeviceObservation,
    RiskEvent,
    VoterDevice,
    VoterProfile,
    VoterSession,
    Vote,
)


SESSION_COOKIE_NAME = 'baiqymyz_session'
DEVICE_COOKIE_NAME = 'baiqymyz_device_id'
SESSION_COOKIE_MAX_AGE = 60 * 60 * 24 * 30
DEVICE_COOKIE_MAX_AGE = 60 * 60 * 24 * 365


class DeviceBindingConflict(Exception):
    def __init__(self, bound_phone_mask):
        self.bound_phone_mask = bound_phone_mask
        super().__init__('Device is bound to another phone number.')

    def as_payload(self):
        return {
            'detail': 'This device is bound to another phone number.',
            'code': 'DEVICE_BOUND_TO_OTHER_PHONE',
            'bound_phone_mask': self.bound_phone_mask,
        }


def get_client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _salt():
    return getattr(settings, 'AUTH_FINGERPRINT_SALT', '') or settings.SECRET_KEY


def hash_value(value):
    if value is None:
        return ''
    normalized = str(value).strip()
    if not normalized:
        return ''
    payload = f'{_salt()}:{normalized}'.encode('utf-8')
    return hashlib.sha256(payload).hexdigest()


def make_session_token():
    return secrets.token_urlsafe(48)


def make_device_id():
    return secrets.token_urlsafe(32)


def get_cookie_options(max_age):
    return {
        'httponly': True,
        'secure': not settings.DEBUG,
        'samesite': 'Lax',
        'max_age': max_age,
    }


def set_auth_cookies(response, session_token, device_id):
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        **get_cookie_options(SESSION_COOKIE_MAX_AGE),
    )
    response.set_cookie(
        key=DEVICE_COOKIE_NAME,
        value=device_id,
        **get_cookie_options(DEVICE_COOKIE_MAX_AGE),
    )


def clear_auth_cookies(response):
    response.delete_cookie(SESSION_COOKIE_NAME, samesite='Lax')
    response.delete_cookie(DEVICE_COOKIE_NAME, samesite='Lax')


def mask_phone(phone):
    digits = ''.join(character for character in str(phone or '') if character.isdigit())
    if len(digits) == 11 and digits.startswith('7'):
        return f'+7 {digits[1:4]} *** ** {digits[-2:]}'
    if len(digits) >= 4:
        return f'***{digits[-4:]}'
    return ''


def get_device_binding(device):
    metadata = device.metadata if isinstance(device.metadata, dict) else {}
    return {
        'phone_hash': metadata.get('bound_phone_hash', ''),
        'phone_mask': metadata.get('bound_phone_mask', ''),
        'user_id': metadata.get('bound_user_id'),
    }


def set_device_binding(device, user, profile):
    metadata = device.metadata if isinstance(device.metadata, dict) else {}
    metadata.update(
        {
            'bound_phone_hash': profile.phone_hash,
            'bound_phone_mask': mask_phone(profile.phone_number),
            'bound_user_id': user.id,
        }
    )
    device.metadata = metadata
    device.save(update_fields=['metadata'])
    return get_device_binding(device)


def ensure_device_binding(device, user, profile):
    binding = get_device_binding(device)
    if binding['phone_hash']:
        return binding

    first_observation = (
        DeviceObservation.objects.select_related('user__voter_profile')
        .filter(device=device)
        .order_by('created_at', 'id')
        .first()
    )
    first_profile = getattr(first_observation.user, 'voter_profile', None) if first_observation else None
    if first_observation and first_profile:
        return set_device_binding(device, first_observation.user, first_profile)

    return set_device_binding(device, user, profile)


def get_device_conflict(user, profile=None, device=None):
    device = device or getattr(user, 'voter_device', None)
    if not device:
        return None
    profile = profile or getattr(user, 'voter_profile', None)
    phone_hash = profile.phone_hash if profile else hash_value(user.get_username())
    binding = get_device_binding(device)
    if binding['phone_hash'] and binding['phone_hash'] != phone_hash:
        return {
            'code': 'DEVICE_BOUND_TO_OTHER_PHONE',
            'bound_phone_mask': binding['phone_mask'],
        }
    return None


def user_payload(user, profile=None, voter_session=None):
    profile = profile or getattr(user, 'voter_profile', None)
    device_conflict = get_device_conflict(user, profile, voter_session.device) if voter_session else None
    return {
        'id': user.id,
        'phone_number': profile.phone_number if profile else user.get_username(),
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
        'session_expires_at': voter_session.expires_at if voter_session else None,
        'device_conflict': bool(device_conflict),
        'device_conflict_code': device_conflict['code'] if device_conflict else '',
        'bound_phone_mask': device_conflict['bound_phone_mask'] if device_conflict else '',
    }


def get_or_create_phone_user(phone):
    User = get_user_model()
    user, _created = User.objects.get_or_create(username=phone)
    if not user.has_usable_password():
        user.set_unusable_password()
        user.save(update_fields=['password'])

    # Keep the legacy phone table populated while old admin/views still exist.
    CustomUser.objects.get_or_create(
        phone_number=phone,
        defaults={'password': make_password(None)},
    )

    profile, _profile_created = VoterProfile.objects.update_or_create(
        user=user,
        defaults={
            'phone_number': phone,
            'phone_hash': hash_value(phone),
        },
    )
    return user, profile


def fingerprint_hashes(validated_data):
    return {
        'browser_fingerprint_hash': hash_value(validated_data.get('browser_fingerprint', '')),
        'soft_fingerprint_hash': hash_value(validated_data.get('soft_fingerprint', '')),
        'network_fingerprint_hash': hash_value(validated_data.get('network_fingerprint', '')),
    }


def fingerprint_binding_key(fingerprints):
    if fingerprints.get('soft_fingerprint_hash'):
        return fingerprints['soft_fingerprint_hash'], 'soft'
    if fingerprints.get('browser_fingerprint_hash'):
        return fingerprints['browser_fingerprint_hash'], 'browser'
    return '', ''


def get_fingerprint_binding(fingerprints):
    fingerprint_hash, _fingerprint_type = fingerprint_binding_key(fingerprints)
    if not fingerprint_hash:
        return None
    return DeviceFingerprintBinding.objects.filter(fingerprint_hash=fingerprint_hash).first()


def ensure_fingerprint_binding(fingerprints, user, profile, device):
    fingerprint_hash, fingerprint_type = fingerprint_binding_key(fingerprints)
    if not fingerprint_hash:
        return None
    binding, created = DeviceFingerprintBinding.objects.get_or_create(
        fingerprint_hash=fingerprint_hash,
        defaults={
            'fingerprint_type': fingerprint_type,
            'phone_hash': profile.phone_hash,
            'phone_mask': mask_phone(profile.phone_number),
            'user': user,
            'device': device,
            'metadata': {'source': 'phone_login'},
        },
    )
    if not created:
        binding.last_seen_at = timezone.now()
        binding.save(update_fields=['last_seen_at'])
    return binding


def get_binding_conflict(profile, device=None, fingerprints=None):
    phone_hash = profile.phone_hash
    if device:
        device_binding = get_device_binding(device)
        if device_binding['phone_hash'] and device_binding['phone_hash'] != phone_hash:
            return DeviceBindingConflict(device_binding['phone_mask'])

    if fingerprints:
        fingerprint_binding = get_fingerprint_binding(fingerprints)
        if fingerprint_binding and fingerprint_binding.phone_hash != phone_hash:
            return DeviceBindingConflict(fingerprint_binding.phone_mask)

    return None


def create_risk_event(user=None, device=None, voter_session=None, vote=None, event_type='', severity=RiskEvent.SEVERITY_LOW, metadata=None):
    return RiskEvent.objects.create(
        user=user,
        device=device,
        voter_session=voter_session,
        vote=vote,
        event_type=event_type,
        severity=severity,
        metadata=metadata or {},
    )


def create_or_update_phone_session(phone, request, validated_data):
    ip_address = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')[:2000]
    fingerprints = fingerprint_hashes(validated_data)
    signals = validated_data.get('signals') if isinstance(validated_data.get('signals'), dict) else {}
    incoming_device_id = request.COOKIES.get(DEVICE_COOKIE_NAME, '')
    incoming_device_hash = hash_value(incoming_device_id)
    cookie_was_missing = not incoming_device_id

    with transaction.atomic():
        user, profile = get_or_create_phone_user(phone)

        device = None
        if incoming_device_hash:
            device = VoterDevice.objects.filter(device_cookie_hash=incoming_device_hash).first()

        binding_conflict = get_binding_conflict(profile, device=device, fingerprints=fingerprints)
        if binding_conflict:
            AuthAuditLog.objects.create(
                event_type=AuthAuditLog.EVENT_PHONE_LOGIN,
                user=user,
                device=device,
                phone_hash=profile.phone_hash,
                ip_address=ip_address,
                user_agent=user_agent,
                result='device_conflict',
                metadata={
                    'code': 'DEVICE_BOUND_TO_OTHER_PHONE',
                    'bound_phone_mask': binding_conflict.bound_phone_mask,
                    'cookie_was_missing': cookie_was_missing,
                },
            )
            raise binding_conflict

        if device is None:
            incoming_device_id = make_device_id()
            device = VoterDevice.objects.create(
                device_id=incoming_device_id,
                device_cookie_hash=hash_value(incoming_device_id),
                metadata={'created_from': 'phone_login'},
            )
        else:
            device.metadata = {**(device.metadata or {}), 'last_login_from': 'phone_login'}
            device.last_seen_at = timezone.now()
            device.save(update_fields=['metadata', 'last_seen_at'])

        device_binding = ensure_device_binding(device, user, profile)
        ensure_fingerprint_binding(fingerprints, user, profile, device)
        device_conflict = get_device_conflict(user, profile, device)

        VoterSession.objects.filter(user=user, device=device, revoked_at__isnull=True).update(
            revoked_at=timezone.now()
        )

        session_token = make_session_token()
        voter_session = VoterSession.objects.create(
            user=user,
            device=device,
            session_hash=hash_value(session_token),
            expires_at=timezone.now() + timedelta(seconds=getattr(settings, 'VOTER_SESSION_TTL_SECONDS', SESSION_COOKIE_MAX_AGE)),
            ip_address=ip_address,
            user_agent=user_agent,
        )

        observation = DeviceObservation.objects.create(
            device=device,
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=signals,
            **fingerprints,
        )

        if device_conflict or DeviceObservation.objects.filter(device=device).exclude(user=user).exists():
            create_risk_event(
                user=user,
                device=device,
                voter_session=voter_session,
                event_type=RiskEvent.EVENT_DEVICE_REUSE_WITH_DIFFERENT_PHONE,
                severity=RiskEvent.SEVERITY_HIGH,
                metadata={
                    'phone_hash': profile.phone_hash,
                    'bound_phone_hash': device_binding.get('phone_hash', ''),
                },
            )

        fingerprint_query = DeviceObservation.objects.exclude(device=device)
        fingerprint_matched = False
        for field, value in fingerprints.items():
            if value and fingerprint_query.filter(**{field: value}).exists():
                fingerprint_matched = True
                break
        if cookie_was_missing and fingerprint_matched:
            create_risk_event(
                user=user,
                device=device,
                voter_session=voter_session,
                event_type=RiskEvent.EVENT_COOKIE_MISSING_BUT_FINGERPRINT_MATCHED,
                severity=RiskEvent.SEVERITY_MEDIUM,
            )

        recent_window = timezone.now() - timedelta(minutes=30)
        if AuthAuditLog.objects.filter(ip_address=ip_address, created_at__gte=recent_window).exclude(phone_hash=profile.phone_hash).count() >= 5:
            create_risk_event(
                user=user,
                device=device,
                voter_session=voter_session,
                event_type=RiskEvent.EVENT_MANY_PHONES_FROM_SAME_IP,
                severity=RiskEvent.SEVERITY_MEDIUM,
            )

        AuthAuditLog.objects.create(
            event_type=AuthAuditLog.EVENT_PHONE_LOGIN,
            user=user,
            device=device,
            voter_session=voter_session,
            phone_hash=profile.phone_hash,
            ip_address=ip_address,
            user_agent=user_agent,
            result='success',
            metadata={'observation_id': observation.id},
        )

    return {
        'user': user,
        'profile': profile,
        'device': device,
        'session': voter_session,
        'session_token': session_token,
        'device_id': incoming_device_id,
        'fingerprints': fingerprints,
    }


def get_active_voter_session_from_request(request):
    token = request.COOKIES.get(SESSION_COOKIE_NAME)
    if not token:
        return None
    session_hash = hash_value(token)
    voter_session = (
        VoterSession.objects.select_related('user', 'device', 'user__voter_profile')
        .filter(session_hash=session_hash, revoked_at__isnull=True, expires_at__gt=timezone.now())
        .first()
    )
    return voter_session


class VoterSessionAuthentication(BaseAuthentication):
    def authenticate_header(self, request):
        return 'Baiqymyz'

    def authenticate(self, request):
        voter_session = get_active_voter_session_from_request(request)
        if not voter_session:
            return None
        if voter_session.device.is_blocked:
            raise AuthenticationFailed('Device is blocked.')
        voter_session.last_seen_at = timezone.now()
        voter_session.save(update_fields=['last_seen_at'])
        request.voter_session = voter_session
        request.voter_device = voter_session.device
        return (voter_session.user, None)


def revoke_current_voter_session(request):
    voter_session = get_active_voter_session_from_request(request)
    if not voter_session:
        return None
    voter_session.revoked_at = timezone.now()
    voter_session.save(update_fields=['revoked_at'])
    AuthAuditLog.objects.create(
        event_type=AuthAuditLog.EVENT_LOGOUT,
        user=voter_session.user,
        device=voter_session.device,
        voter_session=voter_session,
        phone_hash=getattr(getattr(voter_session.user, 'voter_profile', None), 'phone_hash', ''),
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:2000],
        result='success',
    )
    return voter_session


def evaluate_vote_risk(voting, user, participant, request, fingerprints):
    profile = getattr(user, 'voter_profile', None)
    voter_session = getattr(request, 'voter_session', None)
    device = getattr(request, 'voter_device', None)
    phone_hash = profile.phone_hash if profile else hash_value(user.get_username())
    device_id = device.device_id if device else ''
    risk_events = []
    risk_score = 0

    counted_votes = Vote.objects.filter(voting=voting, status__in=Vote.COUNTED_STATUSES)

    if counted_votes.filter(phone_hash=phone_hash).exclude(user=user).exists():
        risk_events.append((RiskEvent.EVENT_PHONE_ALREADY_VOTED, RiskEvent.SEVERITY_HIGH))
        risk_score += 90

    if device_id and counted_votes.filter(device_id=device_id).exclude(user=user).exists():
        risk_events.append((RiskEvent.EVENT_DEVICE_ALREADY_VOTED, RiskEvent.SEVERITY_HIGH))
        risk_score += 90

    soft_fingerprint_hash = fingerprints.get('soft_fingerprint_hash')
    if (
        soft_fingerprint_hash
        and counted_votes.filter(soft_fingerprint_hash=soft_fingerprint_hash).exclude(user=user).exists()
    ):
        risk_events.append((RiskEvent.EVENT_FINGERPRINT_ALREADY_VOTED, RiskEvent.SEVERITY_HIGH))
        risk_score += 90

    browser_fingerprint_hash = fingerprints.get('browser_fingerprint_hash')
    if (
        browser_fingerprint_hash
        and counted_votes.filter(browser_fingerprint_hash=browser_fingerprint_hash).exclude(user=user).exists()
    ):
        risk_events.append((RiskEvent.EVENT_FINGERPRINT_ALREADY_VOTED, RiskEvent.SEVERITY_LOW))
        risk_score += 10

    status = Vote.STATUS_ACCEPTED
    if risk_score >= 80:
        status = Vote.STATUS_PENDING_REVIEW
    elif risk_score >= 40:
        status = Vote.STATUS_ACCEPTED_WITH_FLAG

    return {
        'status': status,
        'risk_score': min(risk_score, 100),
        'risk_events': risk_events,
        'phone_hash': phone_hash,
        'device': device,
        'voter_session': voter_session,
        'device_id': device_id,
        'review_reason': ', '.join(sorted({event for event, _severity in risk_events})),
    }


def attach_vote_risk_events(vote, risk_result):
    for event_type, severity in risk_result['risk_events']:
        create_risk_event(
            user=vote.user,
            device=risk_result.get('device'),
            voter_session=risk_result.get('voter_session'),
            vote=vote,
            event_type=event_type,
            severity=severity,
            metadata={'voting': vote.voting_id, 'participant': vote.participant_id},
        )
