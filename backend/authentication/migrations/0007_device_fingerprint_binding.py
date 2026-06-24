import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def _mask_phone(phone):
    digits = ''.join(character for character in str(phone or '') if character.isdigit())
    if len(digits) == 11 and digits.startswith('7'):
        return f'+7 {digits[1:4]} *** ** {digits[-2:]}'
    if len(digits) >= 4:
        return f'***{digits[-4:]}'
    return ''


def _binding_key(observation):
    if observation.soft_fingerprint_hash:
        return observation.soft_fingerprint_hash, 'soft'
    if observation.browser_fingerprint_hash:
        return observation.browser_fingerprint_hash, 'browser'
    return '', ''


def backfill_bindings(apps, schema_editor):
    DeviceObservation = apps.get_model('authentication', 'DeviceObservation')
    DeviceFingerprintBinding = apps.get_model('authentication', 'DeviceFingerprintBinding')
    VoterDevice = apps.get_model('authentication', 'VoterDevice')
    VoterProfile = apps.get_model('authentication', 'VoterProfile')

    profiles = {
        profile.user_id: profile
        for profile in VoterProfile.objects.all().only('user_id', 'phone_hash', 'phone_number')
    }

    for device in VoterDevice.objects.all().only('id', 'metadata'):
        metadata = device.metadata if isinstance(device.metadata, dict) else {}
        if metadata.get('bound_phone_hash'):
            continue
        observation = (
            DeviceObservation.objects.filter(device_id=device.id)
            .order_by('created_at', 'id')
            .only('user_id')
            .first()
        )
        profile = profiles.get(observation.user_id) if observation else None
        if not profile:
            continue
        metadata.update(
            {
                'bound_phone_hash': profile.phone_hash,
                'bound_phone_mask': _mask_phone(profile.phone_number),
                'bound_user_id': profile.user_id,
            }
        )
        device.metadata = metadata
        device.save(update_fields=['metadata'])

    seen_fingerprints = set()
    for observation in DeviceObservation.objects.order_by('created_at', 'id').only(
        'user_id',
        'device_id',
        'browser_fingerprint_hash',
        'soft_fingerprint_hash',
        'created_at',
    ):
        fingerprint_hash, fingerprint_type = _binding_key(observation)
        if not fingerprint_hash or fingerprint_hash in seen_fingerprints:
            continue
        profile = profiles.get(observation.user_id)
        if not profile:
            continue
        DeviceFingerprintBinding.objects.get_or_create(
            fingerprint_hash=fingerprint_hash,
            defaults={
                'fingerprint_type': fingerprint_type,
                'phone_hash': profile.phone_hash,
                'phone_mask': _mask_phone(profile.phone_number),
                'user_id': profile.user_id,
                'device_id': observation.device_id,
                'metadata': {'source': 'migration_0007_backfill'},
            },
        )
        seen_fingerprints.add(fingerprint_hash)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('authentication', '0006_phone_only_auth_risk_votes'),
    ]

    operations = [
        migrations.CreateModel(
            name='DeviceFingerprintBinding',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fingerprint_hash', models.CharField(max_length=64, unique=True)),
                ('fingerprint_type', models.CharField(default='soft', max_length=32)),
                ('phone_hash', models.CharField(max_length=64)),
                ('phone_mask', models.CharField(blank=True, default='', max_length=32)),
                ('first_seen_at', models.DateTimeField(auto_now_add=True)),
                ('last_seen_at', models.DateTimeField(auto_now=True)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('device', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='fingerprint_bindings', to='authentication.voterdevice')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fingerprint_bindings', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'indexes': [
                    models.Index(fields=['fingerprint_hash'], name='fp_bind_hash_idx'),
                    models.Index(fields=['phone_hash'], name='fp_bind_phone_idx'),
                    models.Index(fields=['user', 'first_seen_at'], name='fp_bind_user_seen_idx'),
                ],
            },
        ),
        migrations.RunPython(backfill_bindings, noop_reverse),
    ]
