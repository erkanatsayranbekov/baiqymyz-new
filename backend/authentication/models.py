from django.conf import settings
from django.db import models
from django.utils import timezone

class CustomUser(models.Model):
    phone_number = models.CharField(verbose_name='Номер телефона', max_length=11, primary_key=True)
    password = models.CharField(max_length=255, verbose_name='Пароль')

    def __str__(self):
        return self.phone_number


class Voting(models.Model):
    STATUS_DRAFT = 'draft'
    STATUS_ACTIVE = 'active'
    STATUS_CLOSED = 'closed'

    STATUS_CHOICES = (
        (STATUS_DRAFT, 'Draft'),
        (STATUS_ACTIVE, 'Active'),
        (STATUS_CLOSED, 'Closed'),
    )

    title = models.CharField(max_length=255)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['status'], name='voting_status_idx'),
            models.Index(fields=['starts_at'], name='voting_starts_idx'),
            models.Index(fields=['ends_at'], name='voting_ends_idx'),
        ]

    def __str__(self):
        return self.title

    def is_active(self):
        now = timezone.now()
        if self.status != self.STATUS_ACTIVE:
            return False
        if self.starts_at and self.starts_at > now:
            return False
        if self.ends_at and self.ends_at < now:
            return False
        return True


class Participant(models.Model):
    voting = models.ForeignKey(
        Voting,
        on_delete=models.CASCADE,
        related_name='participants',
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to='participants', default='default.png')
    location = models.TextField(default='')

    def __str__(self):
        return self.name


class Vote(models.Model):
    voting = models.ForeignKey(
        Voting,
        on_delete=models.CASCADE,
        related_name='votes',
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='votes',
        null=True,
        blank=True,
    )
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='votes')
    score = models.IntegerField(default=1)
    voter_fingerprint = models.CharField(max_length=255)
    voter_ip = models.GenericIPAddressField(null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['voting', 'user'],
                condition=models.Q(voting__isnull=False, user__isnull=False),
                name='unique_active_vote_per_user_voting',
            )
        ]
        indexes = [
            models.Index(fields=['voter_fingerprint'], name='vote_fingerprint_idx'),
            models.Index(fields=['participant', 'voter_ip'], name='vote_participant_ip_idx'),
            models.Index(fields=['participant', 'voter_fingerprint'], name='vote_participant_fp_idx'),
            models.Index(fields=['voting'], name='vote_voting_idx'),
            models.Index(fields=['participant'], name='vote_participant_idx'),
            models.Index(fields=['user'], name='vote_user_idx'),
            models.Index(fields=['voting', 'user'], name='vote_voting_user_idx'),
            models.Index(fields=['voting', 'participant'], name='vote_voting_participant_idx'),
        ]


class VoteHistory(models.Model):
    voting = models.ForeignKey(Voting, on_delete=models.CASCADE, related_name='vote_history')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='vote_history')
    previous_participant = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        related_name='previous_vote_history',
        null=True,
        blank=True,
    )
    new_participant = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        related_name='new_vote_history',
        null=True,
        blank=True,
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')
    device_fingerprint = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['voting', 'user'], name='vote_hist_voting_user_idx'),
            models.Index(fields=['voting', 'created_at'], name='vote_hist_voting_created_idx'),
        ]

    def __str__(self):
        return f'{self.user_id}:{self.voting_id}:{self.previous_participant_id}->{self.new_participant_id}'


class OTPChallenge(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_SENT = 'sent'
    STATUS_VERIFIED = 'verified'
    STATUS_EXPIRED = 'expired'
    STATUS_FAILED = 'failed'
    STATUS_LOCKED = 'locked'

    STATUS_CHOICES = (
        (STATUS_PENDING, 'Pending'),
        (STATUS_SENT, 'Sent'),
        (STATUS_VERIFIED, 'Verified'),
        (STATUS_EXPIRED, 'Expired'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_LOCKED, 'Locked'),
    )

    phone = models.CharField(max_length=16)
    otp_hash = models.CharField(max_length=255)
    purpose = models.CharField(max_length=32, default='login')
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=STATUS_PENDING)
    attempt_count = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=5)
    expires_at = models.DateTimeField()
    sent_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    locked_until = models.DateTimeField(null=True, blank=True)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')
    mobizon_message_id = models.CharField(max_length=64, blank=True, default='')
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['phone'], name='otp_phone_idx'),
            models.Index(fields=['status'], name='otp_status_idx'),
            models.Index(fields=['expires_at'], name='otp_expires_idx'),
            models.Index(fields=['phone', 'purpose', 'status'], name='otp_phone_purp_status_idx'),
            models.Index(fields=['phone', 'status', 'locked_until'], name='otp_phone_status_lock_idx'),
            models.Index(fields=['ip_address', 'created_at'], name='otp_ip_created_idx'),
        ]

    def __str__(self):
        return f'{self.phone}:{self.purpose}:{self.status}'


class ManagerOTPAuditLog(models.Model):
    RESULT_SUCCESS = 'success'
    RESULT_VALIDATION_ERROR = 'validation_error'
    RESULT_RATE_LIMITED = 'rate_limited'
    RESULT_DISABLED = 'disabled'

    RESULT_CHOICES = (
        (RESULT_SUCCESS, 'Success'),
        (RESULT_VALIDATION_ERROR, 'Validation error'),
        (RESULT_RATE_LIMITED, 'Rate limited'),
        (RESULT_DISABLED, 'Disabled'),
    )

    manager_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='manager_otp_audit_logs',
        null=True,
        blank=True,
    )
    phone = models.CharField(max_length=16, blank=True, default='')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')
    result = models.CharField(max_length=32, choices=RESULT_CHOICES)
    error_reason = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['manager_user', 'created_at'], name='mgr_otp_user_created_idx'),
            models.Index(fields=['phone', 'created_at'], name='mgr_otp_phone_created_idx'),
            models.Index(fields=['result', 'created_at'], name='mgr_otp_result_created_idx'),
        ]

    def __str__(self):
        return f'{self.manager_user_id}:{self.phone}:{self.result}'


class ManagerAuthSession(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='manager_auth_sessions',
    )
    token = models.ForeignKey(
        'authtoken.Token',
        on_delete=models.CASCADE,
        related_name='manager_auth_sessions',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    last_seen_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['token', 'expires_at'], name='mgr_auth_token_expires_idx'),
            models.Index(fields=['user', 'created_at'], name='mgr_auth_user_created_idx'),
        ]

    def __str__(self):
        return f'{self.user_id}:{self.token_id}:{self.expires_at}'
