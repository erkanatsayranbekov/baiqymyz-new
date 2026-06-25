from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from .models import (
    DeviceFingerprintBinding,
    ManagerAuthSession,
    OTPChallenge,
    RiskEvent,
    Vote,
    VoteHistory,
    VoterDevice,
    VoterProfile,
    VoterSession,
    Voting,
    Participant,
)
from .otp import OTPService
from .phone_auth import DEVICE_COOKIE_NAME, SESSION_COOKIE_NAME, hash_value


@override_settings(
    AUTH_FINGERPRINT_SALT='unit-test-fingerprint-salt',
    VOTER_SESSION_TTL_SECONDS=60 * 60 * 24 * 30,
    MANAGER_AUTH_ENABLED=True,
    MANAGER_SESSION_TTL_SECONDS=28800,
    PHONE_ONLY_AUTH_ENABLED=True,
)
class PhoneOnlyAuthTests(APITestCase):
    def phone_login(self, phone='+7 (700) 123-45-67', browser_fingerprint='browser-a', soft_fingerprint='soft-a'):
        return self.client.post(
            '/api/auth/phone/',
            {
                'phone': phone,
                'browser_fingerprint': browser_fingerprint,
                'soft_fingerprint': soft_fingerprint,
                'network_fingerprint': 'network-a',
                'signals': {'timezone': 'Asia/Almaty', 'platform': 'test'},
            },
            format='json',
            HTTP_HOST='localhost',
            HTTP_USER_AGENT='phone-auth-test',
            REMOTE_ADDR='127.0.0.1',
        )

    def test_phone_login_creates_user_profile_device_session_and_cookies(self):
        response = self.phone_login()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(SESSION_COOKIE_NAME, response.cookies)
        self.assertIn(DEVICE_COOKIE_NAME, response.cookies)
        self.assertEqual(response.data['user']['phone_number'], '77001234567')
        self.assertTrue(get_user_model().objects.filter(username='77001234567').exists())
        self.assertTrue(VoterProfile.objects.filter(phone_number='77001234567').exists())
        self.assertEqual(VoterDevice.objects.count(), 1)
        self.assertEqual(VoterSession.objects.count(), 1)
        device = VoterDevice.objects.get()
        self.assertEqual(device.metadata['bound_phone_mask'], '+7 700 *** ** 67')
        self.assertEqual(device.metadata['bound_phone_hash'], VoterProfile.objects.get(phone_number='77001234567').phone_hash)
        self.assertEqual(DeviceFingerprintBinding.objects.count(), 1)
        self.assertEqual(DeviceFingerprintBinding.objects.get().phone_mask, '+7 700 *** ** 67')

    def test_repeated_login_on_same_device_reuses_device_and_rotates_session(self):
        self.phone_login()
        first_device_id = self.client.cookies[DEVICE_COOKIE_NAME].value
        first_session = VoterSession.objects.get()

        response = self.phone_login()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.cookies[DEVICE_COOKIE_NAME].value, first_device_id)
        self.assertEqual(VoterDevice.objects.count(), 1)
        self.assertEqual(VoterSession.objects.filter(revoked_at__isnull=True).count(), 1)
        first_session.refresh_from_db()
        self.assertIsNotNone(first_session.revoked_at)

    def test_same_cookie_device_with_different_phone_is_blocked(self):
        self.phone_login('+7 (700) 123-45-67')
        response = self.phone_login('+7 (700) 765-43-21')

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data['code'], 'DEVICE_BOUND_TO_OTHER_PHONE')
        self.assertEqual(response.data['bound_phone_mask'], '+7 700 *** ** 67')
        self.assertEqual(VoterSession.objects.filter(revoked_at__isnull=True).count(), 1)

    def test_auth_me_returns_device_conflict_for_second_phone_on_same_device(self):
        self.phone_login('+7 (700) 123-45-67')
        user = get_user_model().objects.create_user(username='77007654321')
        VoterProfile.objects.create(
            user=user,
            phone_number='77007654321',
            phone_hash=hash_value('77007654321'),
        )
        session = VoterSession.objects.get()
        session.user = user
        session.save(update_fields=['user'])

        response = self.client.get('/api/auth/me/', HTTP_HOST='localhost')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['device_conflict'])
        self.assertEqual(response.data['device_conflict_code'], 'DEVICE_BOUND_TO_OTHER_PHONE')
        self.assertEqual(response.data['bound_phone_mask'], '+7 700 *** ** 67')

    def test_missing_cookie_but_matching_fingerprint_is_blocked(self):
        self.phone_login('+7 (700) 123-45-67', browser_fingerprint='shared-browser', soft_fingerprint='shared-soft')
        self.client.cookies.clear()

        response = self.phone_login('+7 (700) 765-43-21', browser_fingerprint='shared-browser', soft_fingerprint='shared-soft')

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data['code'], 'DEVICE_BOUND_TO_OTHER_PHONE')
        self.assertEqual(response.data['bound_phone_mask'], '+7 700 *** ** 67')

    def test_logout_revokes_session_and_clears_cookies(self):
        self.phone_login()
        session = VoterSession.objects.get()

        response = self.client.post('/api/auth/logout/', {}, format='json', HTTP_HOST='localhost')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        session.refresh_from_db()
        self.assertIsNotNone(session.revoked_at)
        self.assertEqual(response.cookies[SESSION_COOKIE_NAME].value, '')
        self.assertEqual(response.cookies[DEVICE_COOKIE_NAME].value, '')


@override_settings(
    AUTH_FINGERPRINT_SALT='unit-test-fingerprint-salt',
    VOTER_SESSION_TTL_SECONDS=60 * 60 * 24 * 30,
    OTP_AUTH_ENABLED=True,
    PHONE_ONLY_AUTH_ENABLED=False,
    OTP_SECRET='unit-test-otp-secret',
    OTP_RESEND_COOLDOWN_SECONDS=30,
    MOBIZON_API_KEY='unit-test-mobizon-key',
)
class PublicOTPAuthTests(APITestCase):
    def otp_payload(self, phone='+7 (700) 123-45-67', browser_fingerprint='browser-a', soft_fingerprint='soft-a'):
        return {
            'phone': phone,
            'browser_fingerprint': browser_fingerprint,
            'soft_fingerprint': soft_fingerprint,
            'network_fingerprint': 'network-a',
            'signals': {'timezone': 'Asia/Almaty', 'platform': 'test'},
        }

    @patch('authentication.mobizon.MobizonClient.send_message')
    def test_otp_request_creates_challenge_and_sends_sms_via_mobizon(self, send_message):
        send_message.return_value = {'code': 0, 'data': {'messageId': 'message-1'}}

        response = self.client.post(
            '/api/auth/otp/request/',
            self.otp_payload(),
            format='json',
            HTTP_HOST='localhost',
            HTTP_USER_AGENT='otp-auth-test',
            REMOTE_ADDR='127.0.0.1',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['detail'], 'OTP sent')
        self.assertEqual(response.data['resend_after'], 30)
        challenge = OTPChallenge.objects.get(phone='77001234567')
        self.assertEqual(challenge.status, OTPChallenge.STATUS_SENT)
        self.assertEqual(challenge.mobizon_message_id, 'message-1')
        self.assertEqual(challenge.metadata['provider'], 'mobizon')
        send_message.assert_called_once()

    @patch('authentication.mobizon.MobizonClient.send_message')
    def test_otp_verify_sets_voter_session_and_device_cookies(self, send_message):
        send_message.return_value = {'code': 0, 'data': {'messageId': 'message-1'}}
        phone = '77001234567'
        self.client.post(
            '/api/auth/otp/request/',
            self.otp_payload(),
            format='json',
            HTTP_HOST='localhost',
            HTTP_USER_AGENT='otp-auth-test',
            REMOTE_ADDR='127.0.0.1',
        )
        code = OTPService().generate_otp(phone)

        response = self.client.post(
            '/api/auth/otp/verify/',
            {**self.otp_payload(), 'code': code},
            format='json',
            HTTP_HOST='localhost',
            HTTP_USER_AGENT='otp-auth-test',
            REMOTE_ADDR='127.0.0.1',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(SESSION_COOKIE_NAME, response.cookies)
        self.assertIn(DEVICE_COOKIE_NAME, response.cookies)
        self.assertEqual(response.data['user']['phone_number'], phone)
        self.assertTrue(VoterSession.objects.filter(user__username=phone, revoked_at__isnull=True).exists())

        me_response = self.client.get('/api/auth/me/', HTTP_HOST='localhost')
        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        self.assertEqual(me_response.data['phone_number'], phone)

    @patch('authentication.mobizon.MobizonClient.send_message')
    def test_otp_request_with_existing_fingerprint_binding_returns_conflict_without_sms(self, send_message):
        DeviceFingerprintBinding.objects.create(
            fingerprint_hash=hash_value('bound-soft'),
            fingerprint_type='soft',
            phone_hash=hash_value('77001112233'),
            phone_mask='+7 700 *** ** 33',
        )

        response = self.client.post(
            '/api/auth/otp/request/',
            self.otp_payload(
                phone='+7 (700) 444-55-66',
                browser_fingerprint='new-browser',
                soft_fingerprint='bound-soft',
            ),
            format='json',
            HTTP_HOST='localhost',
            HTTP_USER_AGENT='otp-auth-test',
            REMOTE_ADDR='127.0.0.1',
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data['code'], 'DEVICE_BOUND_TO_OTHER_PHONE')
        self.assertEqual(response.data['bound_phone_mask'], '+7 700 *** ** 33')
        self.assertFalse(OTPChallenge.objects.exists())
        send_message.assert_not_called()

    def test_phone_only_endpoint_is_blocked_when_disabled(self):
        response = self.client.post(
            '/api/auth/phone/',
            self.otp_payload(),
            format='json',
            HTTP_HOST='localhost',
        )

        self.assertEqual(response.status_code, status.HTTP_410_GONE)


@override_settings(
    AUTH_FINGERPRINT_SALT='unit-test-fingerprint-salt',
    VOTER_SESSION_TTL_SECONDS=60 * 60 * 24 * 30,
    PHONE_ONLY_AUTH_ENABLED=True,
)
class SingleChoiceVotingTests(APITestCase):
    def setUp(self):
        self.voting = Voting.objects.create(title='Festival voting', status=Voting.STATUS_ACTIVE)
        self.closed_voting = Voting.objects.create(title='Closed voting', status=Voting.STATUS_CLOSED)
        self.participant_a = Participant.objects.create(voting=self.voting, name='Candidate A', location='A')
        self.participant_b = Participant.objects.create(voting=self.voting, name='Candidate B', location='B')
        self.other_participant = Participant.objects.create(voting=self.closed_voting, name='Other candidate', location='Other')

    def phone_login(self, phone='+7 (700) 111-22-33', browser_fingerprint='browser-a'):
        return self.client.post(
            '/api/auth/phone/',
            {
                'phone': phone,
                'browser_fingerprint': browser_fingerprint,
                'soft_fingerprint': f'{browser_fingerprint}-soft',
                'network_fingerprint': 'network-a',
            },
            format='json',
            HTTP_HOST='localhost',
            HTTP_USER_AGENT='vote-test',
            REMOTE_ADDR='127.0.0.1',
        )

    def post_vote(
        self,
        participant=None,
        voting=None,
        latitude=49.459434,
        longitude=75.484896,
        browser_fingerprint='browser-a',
        soft_fingerprint=None,
        network_fingerprint='network-a',
        include_coordinates=True,
        geo_bypass=False,
    ):
        payload = {
            'voting': (voting or self.voting).id,
            'participant': (participant or self.participant_a).id,
            'browser_fingerprint': browser_fingerprint,
            'soft_fingerprint': soft_fingerprint or f'{browser_fingerprint}-soft',
            'network_fingerprint': network_fingerprint,
        }
        if geo_bypass:
            payload['geo_bypass'] = True
        if include_coordinates:
            payload['latitude'] = latitude
            payload['longitude'] = longitude

        return self.client.post(
            '/api/votes/',
            payload,
            format='json',
            HTTP_HOST='localhost',
        )

    def test_phone_session_user_can_vote_first_time(self):
        self.phone_login()
        response = self.post_vote()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        vote = Vote.objects.get(voting=self.voting)
        self.assertEqual(vote.status, Vote.STATUS_ACCEPTED)
        self.assertEqual(vote.latitude, 49.459434)
        self.assertEqual(vote.longitude, 75.484896)
        self.assertEqual(VoteHistory.objects.filter(voting=self.voting, user=vote.user).count(), 1)

    def test_same_candidate_vote_is_idempotent(self):
        self.phone_login()
        self.post_vote()
        response = self.post_vote()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['changed'])
        self.assertEqual(Vote.objects.filter(voting=self.voting).count(), 1)
        self.assertEqual(VoteHistory.objects.filter(voting=self.voting).count(), 1)

    def test_user_can_change_vote(self):
        self.phone_login()
        self.post_vote(self.participant_a)
        response = self.post_vote(self.participant_b, latitude=49.4595, longitude=75.4850)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        vote = Vote.objects.get(voting=self.voting)
        self.assertEqual(vote.participant, self.participant_b)
        self.assertEqual(vote.latitude, 49.4595)
        self.assertEqual(vote.longitude, 75.4850)
        history = VoteHistory.objects.filter(voting=self.voting, user=vote.user).order_by('created_at')
        self.assertEqual(history.count(), 2)
        self.assertEqual(history.last().previous_participant, self.participant_a)
        self.assertEqual(history.last().new_participant, self.participant_b)

    def test_change_vote_without_coordinates_is_rejected(self):
        self.phone_login()
        self.post_vote(self.participant_a)
        response = self.post_vote(self.participant_b, include_coordinates=False)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('latitude', response.data)
        self.assertIn('longitude', response.data)
        self.assertEqual(Vote.objects.get(voting=self.voting).participant, self.participant_a)

    def test_vote_requires_phone_session_cookie(self):
        response = self.post_vote()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_vote_without_coordinates_is_rejected(self):
        self.phone_login()
        response = self.post_vote(include_coordinates=False)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('latitude', response.data)
        self.assertIn('longitude', response.data)

    @override_settings(ALLOW_GEO_BYPASS=True)
    def test_vote_with_dev_geo_bypass_uses_event_coordinates(self):
        self.phone_login()
        response = self.post_vote(include_coordinates=False, geo_bypass=True)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        vote = Vote.objects.get(voting=self.voting)
        self.assertEqual(vote.latitude, 49.459434)
        self.assertEqual(vote.longitude, 75.484896)

    def test_vote_with_invalid_coordinates_is_rejected(self):
        self.phone_login()
        response = self.post_vote(latitude=120, longitude=220)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_vote_outside_event_radius_is_rejected(self):
        self.phone_login()
        response = self.post_vote(latitude=43.2389, longitude=76.8897)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Vote.objects.filter(voting=self.voting).exists())

    def test_closed_voting_rejects_vote(self):
        self.phone_login()
        response = self.post_vote(self.other_participant, self.closed_voting)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_participant_from_another_voting_is_rejected(self):
        self.phone_login()
        response = self.post_vote(self.other_participant, self.voting)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_device_vote_from_different_phone_is_blocked_and_is_excluded_from_results(self):
        self.phone_login('+7 (700) 111-22-33', browser_fingerprint='shared-browser')
        first_response = self.post_vote(self.participant_a, browser_fingerprint='shared-browser')
        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)

        user = get_user_model().objects.create_user(username='77004445566')
        VoterProfile.objects.create(
            user=user,
            phone_number='77004445566',
            phone_hash=hash_value('77004445566'),
        )
        session = VoterSession.objects.get()
        session.user = user
        session.save(update_fields=['user'])
        second_response = self.post_vote(self.participant_b, browser_fingerprint='shared-browser')

        self.assertEqual(second_response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(second_response.data['code'], 'DEVICE_BOUND_TO_OTHER_PHONE')
        self.assertEqual(second_response.data['bound_phone_mask'], '+7 700 *** ** 33')
        self.assertFalse(Vote.objects.filter(participant=self.participant_b).exists())

        results = self.client.get(f'/api/votes/results/?voting={self.voting.id}', HTTP_HOST='localhost')
        self.assertEqual(results.status_code, status.HTTP_200_OK)
        self.assertEqual(results.data['total_votes'], 1)
        candidate_b = next(candidate for candidate in results.data['candidates'] if candidate['id'] == self.participant_b.id)
        self.assertEqual(candidate_b['vote_count'], 0)

    def test_network_fingerprint_match_alone_does_not_make_vote_pending_review(self):
        previous_user = get_user_model().objects.create_user(username='77009990000')
        Vote.objects.create(
            voting=self.voting,
            user=previous_user,
            participant=self.participant_a,
            voter_fingerprint='77009990000',
            voter_ip='127.0.0.10',
            status=Vote.STATUS_ACCEPTED,
            phone_hash=hash_value('77009990000'),
            browser_fingerprint_hash=hash_value('previous-browser'),
            soft_fingerprint_hash=hash_value('previous-soft'),
            network_fingerprint_hash=hash_value('shared-network'),
        )
        self.phone_login('+7 (700) 111-22-33', browser_fingerprint='new-browser')

        response = self.post_vote(
            self.participant_b,
            browser_fingerprint='new-browser',
            soft_fingerprint='new-soft',
            network_fingerprint='shared-network',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        vote = Vote.objects.get(user__username='77001112233')
        self.assertEqual(vote.status, Vote.STATUS_ACCEPTED)
        self.assertEqual(vote.risk_score, 0)
        self.assertEqual(vote.review_reason, '')
        self.assertFalse(RiskEvent.objects.filter(vote=vote).exists())

    def test_browser_fingerprint_match_is_low_risk_and_stays_accepted(self):
        previous_user = get_user_model().objects.create_user(username='77009990000')
        Vote.objects.create(
            voting=self.voting,
            user=previous_user,
            participant=self.participant_a,
            voter_fingerprint='77009990000',
            voter_ip='127.0.0.10',
            status=Vote.STATUS_ACCEPTED,
            phone_hash=hash_value('77009990000'),
            browser_fingerprint_hash=hash_value('shared-browser-risk'),
            soft_fingerprint_hash=hash_value('previous-soft'),
            network_fingerprint_hash=hash_value('previous-network'),
        )
        self.phone_login('+7 (700) 111-22-33', browser_fingerprint='shared-browser-risk')

        response = self.post_vote(
            self.participant_b,
            browser_fingerprint='shared-browser-risk',
            soft_fingerprint='new-soft',
            network_fingerprint='new-network',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        vote = Vote.objects.get(user__username='77001112233')
        self.assertEqual(vote.status, Vote.STATUS_ACCEPTED)
        self.assertEqual(vote.risk_score, 10)
        self.assertEqual(vote.review_reason, RiskEvent.EVENT_FINGERPRINT_ALREADY_VOTED)
        self.assertTrue(
            RiskEvent.objects.filter(
                vote=vote,
                event_type=RiskEvent.EVENT_FINGERPRINT_ALREADY_VOTED,
                severity=RiskEvent.SEVERITY_LOW,
            ).exists()
        )

    def test_soft_fingerprint_match_still_makes_vote_pending_review(self):
        previous_user = get_user_model().objects.create_user(username='77009990000')
        Vote.objects.create(
            voting=self.voting,
            user=previous_user,
            participant=self.participant_a,
            voter_fingerprint='77009990000',
            voter_ip='127.0.0.10',
            status=Vote.STATUS_ACCEPTED,
            phone_hash=hash_value('77009990000'),
            browser_fingerprint_hash=hash_value('previous-browser'),
            soft_fingerprint_hash=hash_value('shared-soft-risk'),
            network_fingerprint_hash=hash_value('previous-network'),
        )
        self.phone_login('+7 (700) 111-22-33', browser_fingerprint='new-browser')

        response = self.post_vote(
            self.participant_b,
            browser_fingerprint='new-browser',
            soft_fingerprint='shared-soft-risk',
            network_fingerprint='new-network',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        vote = Vote.objects.get(user__username='77001112233')
        self.assertEqual(vote.status, Vote.STATUS_PENDING_REVIEW)
        self.assertEqual(vote.risk_score, 90)
        self.assertEqual(vote.review_reason, RiskEvent.EVENT_FINGERPRINT_ALREADY_VOTED)
        self.assertTrue(
            RiskEvent.objects.filter(
                vote=vote,
                event_type=RiskEvent.EVENT_FINGERPRINT_ALREADY_VOTED,
                severity=RiskEvent.SEVERITY_HIGH,
            ).exists()
        )

    def test_results_count_only_accepted_votes_and_return_tie_leaders(self):
        user_a = get_user_model().objects.create_user(username='77001112233')
        user_b = get_user_model().objects.create_user(username='77004445566')
        Vote.objects.create(
            voting=self.voting,
            user=user_a,
            participant=self.participant_a,
            voter_fingerprint='77001112233',
            voter_ip='127.0.0.1',
            status=Vote.STATUS_ACCEPTED,
        )
        Vote.objects.create(
            voting=self.voting,
            user=user_b,
            participant=self.participant_b,
            voter_fingerprint='77004445566',
            voter_ip='127.0.0.2',
            status=Vote.STATUS_ACCEPTED_WITH_FLAG,
        )
        Vote.objects.create(
            voting=self.voting,
            participant=self.participant_a,
            score=5,
            voter_fingerprint='legacy-rating',
            voter_ip='127.0.0.3',
            status=Vote.STATUS_PENDING_REVIEW,
        )

        response = self.client.get(f'/api/votes/results/?voting={self.voting.id}', HTTP_HOST='localhost')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_votes'], 2)
        self.assertEqual(len(response.data['leaders']), 2)
        self.assertEqual({candidate['vote_count'] for candidate in response.data['candidates']}, {1})

    def test_current_vote_endpoint_returns_user_vote(self):
        self.phone_login()
        self.post_vote(self.participant_a)
        response = self.client.get(f'/api/votes/current/?voting={self.voting.id}', HTTP_HOST='localhost')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['vote']['participant'], self.participant_a.id)
        self.assertEqual(response.data['vote']['status'], Vote.STATUS_ACCEPTED)

    def test_database_unique_constraint_blocks_duplicate_user_vote(self):
        user = get_user_model().objects.create_user(username='77001112233')
        Vote.objects.create(
            voting=self.voting,
            user=user,
            participant=self.participant_a,
            voter_fingerprint='77001112233',
            voter_ip='127.0.0.1',
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Vote.objects.create(
                    voting=self.voting,
                    user=user,
                    participant=self.participant_b,
                    voter_fingerprint='77001112233',
                    voter_ip='127.0.0.2',
                )


@override_settings(MANAGER_AUTH_ENABLED=True, MANAGER_SESSION_TTL_SECONDS=28800)
class ManagerPasswordAuthTests(APITestCase):
    def test_manager_password_login_creates_manager_session(self):
        phone = '77001234567'
        manager = get_user_model().objects.create_user(username=phone, password='manager-pass', is_staff=True)

        response = self.client.post(
            '/api/manager/auth/login/',
            {'phone': '+7 (700) 123-45-67', 'password': 'manager-pass'},
            format='json',
            HTTP_HOST='localhost',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['token'])
        self.assertEqual(response.data['user']['username'], phone)
        token = Token.objects.get(user=manager)
        self.assertTrue(ManagerAuthSession.objects.filter(user=manager, token=token, revoked_at__isnull=True).exists())

    def test_manager_password_login_rejects_wrong_password_and_non_staff_generically(self):
        phone = '77001234567'
        get_user_model().objects.create_user(username=phone, password='manager-pass', is_staff=True)
        get_user_model().objects.create_user(username='77007654321', password='manager-pass', is_staff=False)

        wrong_password_response = self.client.post(
            '/api/manager/auth/login/',
            {'phone': '+7 (700) 123-45-67', 'password': 'wrong-pass'},
            format='json',
            HTTP_HOST='localhost',
        )
        non_staff_response = self.client.post(
            '/api/manager/auth/login/',
            {'phone': '+77007654321', 'password': 'manager-pass'},
            format='json',
            HTTP_HOST='localhost',
        )

        self.assertEqual(wrong_password_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(non_staff_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(wrong_password_response.data, non_staff_response.data)

    def test_manager_auth_me_requires_active_manager_session(self):
        phone = '77001234567'
        manager = get_user_model().objects.create_user(username=phone, is_staff=True)
        token = Token.objects.create(user=manager)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response_without_session = self.client.get('/api/manager/auth/me/', HTTP_HOST='localhost')
        self.assertEqual(response_without_session.status_code, status.HTTP_403_FORBIDDEN)

        ManagerAuthSession.objects.create(
            user=manager,
            token=token,
            expires_at=timezone.now() - timedelta(seconds=1),
        )
        expired_response = self.client.get('/api/manager/auth/me/', HTTP_HOST='localhost')
        self.assertEqual(expired_response.status_code, status.HTTP_403_FORBIDDEN)

        ManagerAuthSession.objects.create(
            user=manager,
            token=token,
            expires_at=timezone.now() + timedelta(hours=1),
        )
        active_response = self.client.get('/api/manager/auth/me/', HTTP_HOST='localhost')
        self.assertEqual(active_response.status_code, status.HTTP_200_OK)
        self.assertEqual(active_response.data['username'], phone)

    def test_old_manager_otp_endpoints_are_gone(self):
        response = self.client.post(
            '/api/manager/auth/request-otp/',
            {'phone': '+77001234567', 'password': 'manager-pass'},
            format='json',
            HTTP_HOST='localhost',
        )
        generate_response = self.client.post(
            '/api/manager/otp/generate/',
            {'phone': '+77001234567'},
            format='json',
            HTTP_HOST='localhost',
        )

        self.assertEqual(response.status_code, status.HTTP_410_GONE)
        self.assertEqual(generate_response.status_code, status.HTTP_410_GONE)
