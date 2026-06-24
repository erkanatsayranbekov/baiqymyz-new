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


class VoterProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='voter_profile',
    )
    phone_number = models.CharField(max_length=16, unique=True)
    phone_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['phone_hash'], name='voter_profile_phone_hash_idx'),
        ]

    def __str__(self):
        return self.phone_number


class VoterDevice(models.Model):
    device_id = models.CharField(max_length=64, unique=True)
    device_cookie_hash = models.CharField(max_length=64, unique=True)
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    is_blocked = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['device_cookie_hash'], name='voter_device_cookie_idx'),
            models.Index(fields=['last_seen_at'], name='voter_device_seen_idx'),
        ]

    def __str__(self):
        return self.device_id


class VoterSession(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='voter_sessions',
    )
    device = models.ForeignKey(
        VoterDevice,
        on_delete=models.CASCADE,
        related_name='sessions',
    )
    session_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    last_seen_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'device'],
                condition=models.Q(revoked_at__isnull=True),
                name='unique_active_voter_session_user_device',
            )
        ]
        indexes = [
            models.Index(fields=['session_hash', 'expires_at'], name='voter_session_hash_exp_idx'),
            models.Index(fields=['user', 'created_at'], name='voter_session_user_created_idx'),
            models.Index(fields=['device', 'created_at'], name='voter_sess_dev_created_idx'),
        ]

    def is_active(self):
        return self.revoked_at is None and self.expires_at > timezone.now()

    def __str__(self):
        return f'{self.user_id}:{self.device_id}:{self.expires_at}'


class DeviceObservation(models.Model):
    device = models.ForeignKey(
        VoterDevice,
        on_delete=models.CASCADE,
        related_name='observations',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='device_observations',
    )
    browser_fingerprint_hash = models.CharField(max_length=64, blank=True, default='')
    soft_fingerprint_hash = models.CharField(max_length=64, blank=True, default='')
    network_fingerprint_hash = models.CharField(max_length=64, blank=True, default='')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['device', 'created_at'], name='device_obs_device_created_idx'),
            models.Index(fields=['user', 'created_at'], name='device_obs_user_created_idx'),
            models.Index(fields=['browser_fingerprint_hash'], name='device_obs_browser_fp_idx'),
            models.Index(fields=['soft_fingerprint_hash'], name='device_obs_soft_fp_idx'),
            models.Index(fields=['network_fingerprint_hash'], name='device_obs_network_fp_idx'),
            models.Index(fields=['ip_address', 'created_at'], name='device_obs_ip_created_idx'),
        ]


class DeviceFingerprintBinding(models.Model):
    fingerprint_hash = models.CharField(max_length=64, unique=True)
    fingerprint_type = models.CharField(max_length=32, default='soft')
    phone_hash = models.CharField(max_length=64)
    phone_mask = models.CharField(max_length=32, blank=True, default='')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='fingerprint_bindings',
    )
    device = models.ForeignKey(
        VoterDevice,
        on_delete=models.SET_NULL,
        related_name='fingerprint_bindings',
        null=True,
        blank=True,
    )
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['fingerprint_hash'], name='fp_bind_hash_idx'),
            models.Index(fields=['phone_hash'], name='fp_bind_phone_idx'),
            models.Index(fields=['user', 'first_seen_at'], name='fp_bind_user_seen_idx'),
        ]

    def __str__(self):
        return f'{self.fingerprint_type}:{self.phone_mask or self.phone_hash}'


class Vote(models.Model):
    STATUS_ACCEPTED = 'accepted'
    STATUS_ACCEPTED_WITH_FLAG = 'accepted_with_flag'
    STATUS_PENDING_REVIEW = 'pending_review'
    STATUS_REJECTED = 'rejected'
    COUNTED_STATUSES = (STATUS_ACCEPTED, STATUS_ACCEPTED_WITH_FLAG)
    STATUS_CHOICES = (
        (STATUS_ACCEPTED, 'Accepted'),
        (STATUS_ACCEPTED_WITH_FLAG, 'Accepted with flag'),
        (STATUS_PENDING_REVIEW, 'Pending review'),
        (STATUS_REJECTED, 'Rejected'),
    )

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
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=STATUS_ACCEPTED)
    phone_hash = models.CharField(max_length=64, blank=True, default='')
    voter_device = models.ForeignKey(
        VoterDevice,
        on_delete=models.SET_NULL,
        related_name='votes',
        null=True,
        blank=True,
    )
    voter_session = models.ForeignKey(
        VoterSession,
        on_delete=models.SET_NULL,
        related_name='votes',
        null=True,
        blank=True,
    )
    device_id = models.CharField(max_length=64, blank=True, default='')
    browser_fingerprint_hash = models.CharField(max_length=64, blank=True, default='')
    soft_fingerprint_hash = models.CharField(max_length=64, blank=True, default='')
    network_fingerprint_hash = models.CharField(max_length=64, blank=True, default='')
    risk_score = models.PositiveSmallIntegerField(default=0)
    review_reason = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['voting', 'user'],
                condition=models.Q(voting__isnull=False, user__isnull=False),
                name='unique_active_vote_per_user_voting',
            ),
            models.UniqueConstraint(
                fields=['voting', 'phone_hash'],
                condition=(
                    models.Q(status__in=['accepted', 'accepted_with_flag'])
                    & ~models.Q(phone_hash='')
                    & models.Q(voting__isnull=False)
                ),
                name='unique_counted_vote_per_phone_voting',
            ),
            models.UniqueConstraint(
                fields=['voting', 'device_id'],
                condition=(
                    models.Q(status__in=['accepted', 'accepted_with_flag'])
                    & ~models.Q(device_id='')
                    & models.Q(voting__isnull=False)
                ),
                name='unique_counted_vote_per_device_voting',
            ),
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
            models.Index(fields=['status'], name='vote_status_idx'),
            models.Index(fields=['phone_hash'], name='vote_phone_hash_idx'),
            models.Index(fields=['device_id'], name='vote_device_id_idx'),
            models.Index(fields=['browser_fingerprint_hash'], name='vote_browser_fp_idx'),
            models.Index(fields=['soft_fingerprint_hash'], name='vote_soft_fp_idx'),
            models.Index(fields=['network_fingerprint_hash'], name='vote_network_fp_idx'),
        ]


class RiskEvent(models.Model):
    SEVERITY_LOW = 'low'
    SEVERITY_MEDIUM = 'medium'
    SEVERITY_HIGH = 'high'
    SEVERITY_CHOICES = (
        (SEVERITY_LOW, 'Low'),
        (SEVERITY_MEDIUM, 'Medium'),
        (SEVERITY_HIGH, 'High'),
    )

    EVENT_DEVICE_REUSE_WITH_DIFFERENT_PHONE = 'DEVICE_REUSE_WITH_DIFFERENT_PHONE'
    EVENT_COOKIE_MISSING_BUT_FINGERPRINT_MATCHED = 'COOKIE_MISSING_BUT_FINGERPRINT_MATCHED'
    EVENT_VPN_SUSPECTED = 'VPN_SUSPECTED'
    EVENT_INCOGNITO_SUSPECTED = 'INCOGNITO_SUSPECTED'
    EVENT_MANY_PHONES_FROM_SAME_IP = 'MANY_PHONES_FROM_SAME_IP'
    EVENT_MANY_DEVICES_FROM_SAME_IP = 'MANY_DEVICES_FROM_SAME_IP'
    EVENT_FINGERPRINT_ALREADY_VOTED = 'FINGERPRINT_ALREADY_VOTED'
    EVENT_USER_AGENT_COLLISION = 'USER_AGENT_COLLISION'
    EVENT_RAPID_REGISTRATION_ATTEMPTS = 'RAPID_REGISTRATION_ATTEMPTS'
    EVENT_PHONE_ALREADY_VOTED = 'PHONE_ALREADY_VOTED'
    EVENT_DEVICE_ALREADY_VOTED = 'DEVICE_ALREADY_VOTED'
    EVENT_USER_ALREADY_VOTED = 'USER_ALREADY_VOTED'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    device = models.ForeignKey(VoterDevice, on_delete=models.SET_NULL, null=True, blank=True)
    voter_session = models.ForeignKey(VoterSession, on_delete=models.SET_NULL, null=True, blank=True)
    vote = models.ForeignKey(Vote, on_delete=models.SET_NULL, null=True, blank=True, related_name='risk_events')
    event_type = models.CharField(max_length=64)
    severity = models.CharField(max_length=16, choices=SEVERITY_CHOICES, default=SEVERITY_LOW)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['event_type', 'created_at'], name='risk_event_type_created_idx'),
            models.Index(fields=['severity', 'created_at'], name='risk_event_sev_created_idx'),
            models.Index(fields=['user', 'created_at'], name='risk_event_user_created_idx'),
            models.Index(fields=['device', 'created_at'], name='risk_event_device_created_idx'),
        ]


class AuthAuditLog(models.Model):
    EVENT_PHONE_LOGIN = 'phone_login'
    EVENT_LOGOUT = 'logout'
    EVENT_MANAGER_LOGIN = 'manager_login'
    EVENT_CHOICES = (
        (EVENT_PHONE_LOGIN, 'Phone login'),
        (EVENT_LOGOUT, 'Logout'),
        (EVENT_MANAGER_LOGIN, 'Manager login'),
    )

    event_type = models.CharField(max_length=32, choices=EVENT_CHOICES)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    device = models.ForeignKey(VoterDevice, on_delete=models.SET_NULL, null=True, blank=True)
    voter_session = models.ForeignKey(VoterSession, on_delete=models.SET_NULL, null=True, blank=True)
    phone_hash = models.CharField(max_length=64, blank=True, default='')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')
    result = models.CharField(max_length=32, blank=True, default='')
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['event_type', 'created_at'], name='auth_audit_event_created_idx'),
            models.Index(fields=['phone_hash', 'created_at'], name='auth_audit_phone_created_idx'),
            models.Index(fields=['user', 'created_at'], name='auth_audit_user_created_idx'),
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
