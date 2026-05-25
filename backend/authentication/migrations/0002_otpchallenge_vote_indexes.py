# Generated manually from the implementation plan.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='OTPChallenge',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone', models.CharField(max_length=16)),
                ('otp_hash', models.CharField(max_length=255)),
                ('purpose', models.CharField(default='login', max_length=32)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('sent', 'Sent'), ('verified', 'Verified'), ('expired', 'Expired'), ('failed', 'Failed'), ('locked', 'Locked')], default='pending', max_length=32)),
                ('attempt_count', models.PositiveIntegerField(default=0)),
                ('max_attempts', models.PositiveIntegerField(default=5)),
                ('expires_at', models.DateTimeField()),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('verified_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True, default='')),
                ('mobizon_message_id', models.CharField(blank=True, default='', max_length=64)),
                ('metadata', models.JSONField(blank=True, default=dict)),
            ],
        ),
        migrations.AddIndex(
            model_name='vote',
            index=models.Index(fields=['voter_fingerprint'], name='vote_fingerprint_idx'),
        ),
        migrations.AddIndex(
            model_name='vote',
            index=models.Index(fields=['participant', 'voter_ip'], name='vote_participant_ip_idx'),
        ),
        migrations.AddIndex(
            model_name='vote',
            index=models.Index(fields=['participant', 'voter_fingerprint'], name='vote_participant_fp_idx'),
        ),
        migrations.AddIndex(
            model_name='otpchallenge',
            index=models.Index(fields=['phone'], name='otp_phone_idx'),
        ),
        migrations.AddIndex(
            model_name='otpchallenge',
            index=models.Index(fields=['status'], name='otp_status_idx'),
        ),
        migrations.AddIndex(
            model_name='otpchallenge',
            index=models.Index(fields=['expires_at'], name='otp_expires_idx'),
        ),
        migrations.AddIndex(
            model_name='otpchallenge',
            index=models.Index(fields=['phone', 'purpose', 'status'], name='otp_phone_purp_status_idx'),
        ),
        migrations.AddIndex(
            model_name='otpchallenge',
            index=models.Index(fields=['ip_address', 'created_at'], name='otp_ip_created_idx'),
        ),
    ]
