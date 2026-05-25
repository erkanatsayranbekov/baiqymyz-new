from celery import shared_task
from .models import OTPChallenge, Vote
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

@shared_task
def insert_vote_task(participant_id, fingerprint, score, ip, lat, lon):
    Vote.objects.update_or_create(
        participant_id=participant_id,
        voter_fingerprint=fingerprint,
        voter_ip=ip,
        defaults={
            'score': score,
            'latitude': lat,
            'longitude': lon,
        }
    )


@shared_task
def cleanup_expired_otp_challenges():
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
    return {'expired': expired_count, 'deleted': deleted_count}
