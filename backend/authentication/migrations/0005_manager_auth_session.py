# Generated manually for manager password + OTP sessions.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('authtoken', '0001_initial'),
        ('authentication', '0004_deterministic_otp_manager_audit'),
    ]

    operations = [
        migrations.CreateModel(
            name='ManagerAuthSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField()),
                ('last_seen_at', models.DateTimeField(blank=True, null=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True, default='')),
                ('revoked_at', models.DateTimeField(blank=True, null=True)),
                ('token', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='manager_auth_sessions', to='authtoken.token')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='manager_auth_sessions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'indexes': [
                    models.Index(fields=['token', 'expires_at'], name='mgr_auth_token_expires_idx'),
                    models.Index(fields=['user', 'created_at'], name='mgr_auth_user_created_idx'),
                ],
            },
        ),
    ]
