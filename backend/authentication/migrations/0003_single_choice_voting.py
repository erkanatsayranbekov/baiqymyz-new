# Generated manually for the single-choice voting migration.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def create_default_voting(apps, schema_editor):
    Voting = apps.get_model('authentication', 'Voting')
    Participant = apps.get_model('authentication', 'Participant')

    voting, _created = Voting.objects.get_or_create(
        title='Default voting',
        defaults={'status': 'active'},
    )
    Participant.objects.filter(voting__isnull=True).update(voting=voting)


def noop_reverse(apps, schema_editor):
    pass


def backfill_vote_updated_at(apps, schema_editor):
    Vote = apps.get_model('authentication', 'Vote')
    for vote in Vote.objects.filter(updated_at__isnull=True).only('id', 'created_at'):
        vote.updated_at = vote.created_at
        vote.save(update_fields=['updated_at'])


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('authentication', '0002_otpchallenge_vote_indexes'),
    ]

    operations = [
        migrations.CreateModel(
            name='Voting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('active', 'Active'), ('closed', 'Closed')], default='draft', max_length=16)),
                ('starts_at', models.DateTimeField(blank=True, null=True)),
                ('ends_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'indexes': [
                    models.Index(fields=['status'], name='voting_status_idx'),
                    models.Index(fields=['starts_at'], name='voting_starts_idx'),
                    models.Index(fields=['ends_at'], name='voting_ends_idx'),
                ],
            },
        ),
        migrations.AddField(
            model_name='participant',
            name='voting',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='participants', to='authentication.voting'),
        ),
        migrations.AddField(
            model_name='vote',
            name='voting',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='votes', to='authentication.voting'),
        ),
        migrations.AddField(
            model_name='vote',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='votes', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='vote',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
        migrations.AlterField(
            model_name='vote',
            name='score',
            field=models.IntegerField(default=1),
        ),
        migrations.CreateModel(
            name='VoteHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True, default='')),
                ('device_fingerprint', models.CharField(blank=True, default='', max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('new_participant', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='new_vote_history', to='authentication.participant')),
                ('previous_participant', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='previous_vote_history', to='authentication.participant')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='vote_history', to=settings.AUTH_USER_MODEL)),
                ('voting', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='vote_history', to='authentication.voting')),
            ],
            options={
                'indexes': [
                    models.Index(fields=['voting', 'user'], name='vote_hist_voting_user_idx'),
                    models.Index(fields=['voting', 'created_at'], name='vote_hist_voting_created_idx'),
                ],
            },
        ),
        migrations.RunPython(create_default_voting, noop_reverse),
        migrations.RunPython(backfill_vote_updated_at, noop_reverse),
        migrations.AlterField(
            model_name='vote',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterUniqueTogether(
            name='vote',
            unique_together=set(),
        ),
        migrations.AddIndex(
            model_name='vote',
            index=models.Index(fields=['voting'], name='vote_voting_idx'),
        ),
        migrations.AddIndex(
            model_name='vote',
            index=models.Index(fields=['participant'], name='vote_participant_idx'),
        ),
        migrations.AddIndex(
            model_name='vote',
            index=models.Index(fields=['user'], name='vote_user_idx'),
        ),
        migrations.AddIndex(
            model_name='vote',
            index=models.Index(fields=['voting', 'user'], name='vote_voting_user_idx'),
        ),
        migrations.AddIndex(
            model_name='vote',
            index=models.Index(fields=['voting', 'participant'], name='vote_voting_participant_idx'),
        ),
        migrations.AddConstraint(
            model_name='vote',
            constraint=models.UniqueConstraint(
                condition=models.Q(('user__isnull', False), ('voting__isnull', False)),
                fields=('voting', 'user'),
                name='unique_active_vote_per_user_voting',
            ),
        ),
    ]
