# Generated manually for phone-only auth, device sessions, and vote risk statuses.

import hashlib
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def _hash_value(value):
    normalized = str(value or '').strip()
    if not normalized:
        return ''
    salt = getattr(settings, 'AUTH_FINGERPRINT_SALT', '') or settings.SECRET_KEY
    return hashlib.sha256(f'{salt}:{normalized}'.encode('utf-8')).hexdigest()


def backfill_phone_profiles_and_vote_hashes(apps, schema_editor):
    User = apps.get_model(settings.AUTH_USER_MODEL.split('.')[0], settings.AUTH_USER_MODEL.split('.')[1])
    VoterProfile = apps.get_model('authentication', 'VoterProfile')
    Vote = apps.get_model('authentication', 'Vote')

    for user in User.objects.all().only('id', 'username'):
        username = str(user.username or '')
        if len(username) == 11 and username.startswith('7') and username.isdigit():
            VoterProfile.objects.update_or_create(
                user_id=user.id,
                defaults={
                    'phone_number': username,
                    'phone_hash': _hash_value(username),
                },
            )

    for vote in Vote.objects.select_related('user').filter(user__isnull=False, phone_hash=''):
        username = str(vote.user.username or '')
        if len(username) == 11 and username.startswith('7') and username.isdigit():
            vote.phone_hash = _hash_value(username)
            vote.save(update_fields=['phone_hash'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('authentication', '0005_manager_auth_session'),
    ]

    operations = [
        migrations.CreateModel(
            name='VoterDevice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('device_id', models.CharField(max_length=64, unique=True)),
                ('device_cookie_hash', models.CharField(max_length=64, unique=True)),
                ('first_seen_at', models.DateTimeField(auto_now_add=True)),
                ('last_seen_at', models.DateTimeField(auto_now=True)),
                ('is_blocked', models.BooleanField(default=False)),
                ('metadata', models.JSONField(blank=True, default=dict)),
            ],
            options={
                'indexes': [
                    models.Index(fields=['device_cookie_hash'], name='voter_device_cookie_idx'),
                    models.Index(fields=['last_seen_at'], name='voter_device_seen_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='VoterProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone_number', models.CharField(max_length=16, unique=True)),
                ('phone_hash', models.CharField(max_length=64, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='voter_profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'indexes': [
                    models.Index(fields=['phone_hash'], name='voter_profile_phone_hash_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='VoterSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_hash', models.CharField(max_length=64, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField()),
                ('last_seen_at', models.DateTimeField(blank=True, null=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True, default='')),
                ('revoked_at', models.DateTimeField(blank=True, null=True)),
                ('device', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sessions', to='authentication.voterdevice')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='voter_sessions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'indexes': [
                    models.Index(fields=['session_hash', 'expires_at'], name='voter_session_hash_exp_idx'),
                    models.Index(fields=['user', 'created_at'], name='voter_session_user_created_idx'),
                    models.Index(fields=['device', 'created_at'], name='voter_sess_dev_created_idx'),
                ],
                'constraints': [
                    models.UniqueConstraint(condition=models.Q(('revoked_at__isnull', True)), fields=('user', 'device'), name='unique_active_voter_session_user_device'),
                ],
            },
        ),
        migrations.CreateModel(
            name='DeviceObservation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('browser_fingerprint_hash', models.CharField(blank=True, default='', max_length=64)),
                ('soft_fingerprint_hash', models.CharField(blank=True, default='', max_length=64)),
                ('network_fingerprint_hash', models.CharField(blank=True, default='', max_length=64)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True, default='')),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('device', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='observations', to='authentication.voterdevice')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='device_observations', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'indexes': [
                    models.Index(fields=['device', 'created_at'], name='device_obs_device_created_idx'),
                    models.Index(fields=['user', 'created_at'], name='device_obs_user_created_idx'),
                    models.Index(fields=['browser_fingerprint_hash'], name='device_obs_browser_fp_idx'),
                    models.Index(fields=['soft_fingerprint_hash'], name='device_obs_soft_fp_idx'),
                    models.Index(fields=['network_fingerprint_hash'], name='device_obs_network_fp_idx'),
                    models.Index(fields=['ip_address', 'created_at'], name='device_obs_ip_created_idx'),
                ],
            },
        ),
        migrations.AddField(
            model_name='vote',
            name='status',
            field=models.CharField(choices=[('accepted', 'Accepted'), ('accepted_with_flag', 'Accepted with flag'), ('pending_review', 'Pending review'), ('rejected', 'Rejected')], default='accepted', max_length=32),
        ),
        migrations.AddField(
            model_name='vote',
            name='phone_hash',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
        migrations.AddField(
            model_name='vote',
            name='device_id',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
        migrations.AddField(
            model_name='vote',
            name='browser_fingerprint_hash',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
        migrations.AddField(
            model_name='vote',
            name='soft_fingerprint_hash',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
        migrations.AddField(
            model_name='vote',
            name='network_fingerprint_hash',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
        migrations.AddField(
            model_name='vote',
            name='risk_score',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='vote',
            name='review_reason',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='vote',
            name='voter_device',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='votes', to='authentication.voterdevice'),
        ),
        migrations.AddField(
            model_name='vote',
            name='voter_session',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='votes', to='authentication.votersession'),
        ),
        migrations.RunPython(backfill_phone_profiles_and_vote_hashes, noop_reverse),
        migrations.CreateModel(
            name='RiskEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_type', models.CharField(max_length=64)),
                ('severity', models.CharField(choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')], default='low', max_length=16)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('device', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='authentication.voterdevice')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('vote', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='risk_events', to='authentication.vote')),
                ('voter_session', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='authentication.votersession')),
            ],
            options={
                'indexes': [
                    models.Index(fields=['event_type', 'created_at'], name='risk_event_type_created_idx'),
                    models.Index(fields=['severity', 'created_at'], name='risk_event_sev_created_idx'),
                    models.Index(fields=['user', 'created_at'], name='risk_event_user_created_idx'),
                    models.Index(fields=['device', 'created_at'], name='risk_event_device_created_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='AuthAuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_type', models.CharField(choices=[('phone_login', 'Phone login'), ('logout', 'Logout'), ('manager_login', 'Manager login')], max_length=32)),
                ('phone_hash', models.CharField(blank=True, default='', max_length=64)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True, default='')),
                ('result', models.CharField(blank=True, default='', max_length=32)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('device', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='authentication.voterdevice')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('voter_session', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='authentication.votersession')),
            ],
            options={
                'indexes': [
                    models.Index(fields=['event_type', 'created_at'], name='auth_audit_event_created_idx'),
                    models.Index(fields=['phone_hash', 'created_at'], name='auth_audit_phone_created_idx'),
                    models.Index(fields=['user', 'created_at'], name='auth_audit_user_created_idx'),
                ],
            },
        ),
        migrations.AddIndex(
            model_name='vote',
            index=models.Index(fields=['status'], name='vote_status_idx'),
        ),
        migrations.AddIndex(
            model_name='vote',
            index=models.Index(fields=['phone_hash'], name='vote_phone_hash_idx'),
        ),
        migrations.AddIndex(
            model_name='vote',
            index=models.Index(fields=['device_id'], name='vote_device_id_idx'),
        ),
        migrations.AddIndex(
            model_name='vote',
            index=models.Index(fields=['browser_fingerprint_hash'], name='vote_browser_fp_idx'),
        ),
        migrations.AddIndex(
            model_name='vote',
            index=models.Index(fields=['soft_fingerprint_hash'], name='vote_soft_fp_idx'),
        ),
        migrations.AddIndex(
            model_name='vote',
            index=models.Index(fields=['network_fingerprint_hash'], name='vote_network_fp_idx'),
        ),
        migrations.AddConstraint(
            model_name='vote',
            constraint=models.UniqueConstraint(
                condition=(
                    models.Q(status__in=['accepted', 'accepted_with_flag'])
                    & ~models.Q(phone_hash='')
                    & models.Q(voting__isnull=False)
                ),
                fields=('voting', 'phone_hash'),
                name='unique_counted_vote_per_phone_voting',
            ),
        ),
        migrations.AddConstraint(
            model_name='vote',
            constraint=models.UniqueConstraint(
                condition=(
                    models.Q(status__in=['accepted', 'accepted_with_flag'])
                    & ~models.Q(device_id='')
                    & models.Q(voting__isnull=False)
                ),
                fields=('voting', 'device_id'),
                name='unique_counted_vote_per_device_voting',
            ),
        ),
    ]
