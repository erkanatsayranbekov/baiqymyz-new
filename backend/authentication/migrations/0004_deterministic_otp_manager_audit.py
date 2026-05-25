# Generated manually for deterministic OTP and manager audit logging.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('authentication', '0003_single_choice_voting'),
    ]

    operations = [
        migrations.AddField(
            model_name='otpchallenge',
            name='last_attempt_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='otpchallenge',
            name='locked_until',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name='otpchallenge',
            index=models.Index(fields=['phone', 'status', 'locked_until'], name='otp_phone_status_lock_idx'),
        ),
        migrations.CreateModel(
            name='ManagerOTPAuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone', models.CharField(blank=True, default='', max_length=16)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True, default='')),
                ('result', models.CharField(choices=[('success', 'Success'), ('validation_error', 'Validation error'), ('rate_limited', 'Rate limited'), ('disabled', 'Disabled')], max_length=32)),
                ('error_reason', models.CharField(blank=True, default='', max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('manager_user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='manager_otp_audit_logs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'indexes': [
                    models.Index(fields=['manager_user', 'created_at'], name='mgr_otp_user_created_idx'),
                    models.Index(fields=['phone', 'created_at'], name='mgr_otp_phone_created_idx'),
                    models.Index(fields=['result', 'created_at'], name='mgr_otp_result_created_idx'),
                ],
            },
        ),
    ]
