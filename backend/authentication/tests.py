from unittest.mock import patch
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.db import IntegrityError, transaction
from django.test import override_settings
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIRequestFactory
from rest_framework.test import APITestCase
from rest_framework.throttling import ScopedRateThrottle
from django.utils import timezone

from .models import ManagerAuthSession, ManagerOTPAuditLog, OTPChallenge, Participant, Vote, VoteHistory, Voting
from .otp import OTPService, OTPVerificationError
from .serializers import normalize_phone


class DummyMobizonClient:
    def __init__(self):
        self.messages = []

    def send_sms(self, recipient, text):
        self.messages.append((recipient, text))
        return {'messageId': 'test-message-id'}


class SingleChoiceVotingTests(APITestCase):
    def setUp(self):
        self.voting = Voting.objects.create(title='Festival voting', status=Voting.STATUS_ACTIVE)
        self.closed_voting = Voting.objects.create(title='Closed voting', status=Voting.STATUS_CLOSED)
        self.participant_a = Participant.objects.create(
            voting=self.voting,
            name='Candidate A',
            location='A',
        )
        self.participant_b = Participant.objects.create(
            voting=self.voting,
            name='Candidate B',
            location='B',
        )
        self.other_participant = Participant.objects.create(
            voting=self.closed_voting,
            name='Other candidate',
            location='Other',
        )
        self.user = get_user_model().objects.create_user(username='77001112233')
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

    def post_vote(self, participant=None, voting=None):
        return self.client.post(
            '/api/votes/',
            {
                'voting': (voting or self.voting).id,
                'participant': (participant or self.participant_a).id,
                'latitude': 51.0698,
                'longitude': 71.3868,
            },
            format='json',
            HTTP_HOST='localhost',
        )

    def test_authenticated_user_can_vote_first_time(self):
        response = self.post_vote()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        vote = Vote.objects.get(voting=self.voting, user=self.user)
        self.assertEqual(Vote.objects.filter(voting=self.voting, user=self.user).count(), 1)
        self.assertEqual(vote.latitude, 51.0698)
        self.assertEqual(vote.longitude, 71.3868)
        self.assertEqual(VoteHistory.objects.filter(voting=self.voting, user=self.user).count(), 1)

    def test_same_candidate_vote_is_idempotent(self):
        self.post_vote()
        response = self.post_vote()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['changed'])
        self.assertEqual(Vote.objects.filter(voting=self.voting, user=self.user).count(), 1)
        self.assertEqual(VoteHistory.objects.filter(voting=self.voting, user=self.user).count(), 1)

    def test_user_can_change_vote(self):
        self.post_vote(self.participant_a)
        response = self.post_vote(self.participant_b)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        vote = Vote.objects.get(voting=self.voting, user=self.user)
        self.assertEqual(vote.participant, self.participant_b)
        history = VoteHistory.objects.filter(voting=self.voting, user=self.user).order_by('created_at')
        self.assertEqual(history.count(), 2)
        self.assertEqual(history.last().previous_participant, self.participant_a)
        self.assertEqual(history.last().new_participant, self.participant_b)

    def test_vote_without_coordinates_is_rejected(self):
        response = self.client.post(
            '/api/votes/',
            {
                'voting': self.voting.id,
                'participant': self.participant_a.id,
            },
            format='json',
            HTTP_HOST='localhost',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('latitude', response.data)
        self.assertIn('longitude', response.data)

    def test_vote_with_invalid_coordinates_is_rejected(self):
        response = self.client.post(
            '/api/votes/',
            {
                'voting': self.voting.id,
                'participant': self.participant_a.id,
                'latitude': 120,
                'longitude': 220,
            },
            format='json',
            HTTP_HOST='localhost',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_vote_outside_event_radius_is_rejected(self):
        response = self.client.post(
            '/api/votes/',
            {
                'voting': self.voting.id,
                'participant': self.participant_a.id,
                'latitude': 43.2389,
                'longitude': 76.8897,
            },
            format='json',
            HTTP_HOST='localhost',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Vote.objects.filter(voting=self.voting, user=self.user).exists())

    def test_unauthenticated_user_cannot_vote(self):
        self.client.credentials()
        response = self.post_vote()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_closed_voting_rejects_vote(self):
        response = self.post_vote(self.other_participant, self.closed_voting)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_participant_from_another_voting_is_rejected(self):
        response = self.post_vote(self.other_participant, self.voting)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_results_count_votes_and_return_tie_leaders(self):
        other_user = get_user_model().objects.create_user(username='77004445566')
        Vote.objects.create(
            voting=self.voting,
            user=self.user,
            participant=self.participant_a,
            voter_fingerprint='77001112233',
            voter_ip='127.0.0.1',
        )
        Vote.objects.create(
            voting=self.voting,
            user=other_user,
            participant=self.participant_b,
            voter_fingerprint='77004445566',
            voter_ip='127.0.0.2',
        )
        Vote.objects.create(
            voting=self.voting,
            participant=self.participant_a,
            score=5,
            voter_fingerprint='legacy-rating',
            voter_ip='127.0.0.3',
        )

        response = self.client.get(f'/api/votes/results/?voting={self.voting.id}', HTTP_HOST='localhost')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_votes'], 2)
        self.assertEqual(len(response.data['leaders']), 2)
        self.assertEqual({candidate['vote_count'] for candidate in response.data['candidates']}, {1})

    def test_current_vote_endpoint_returns_user_vote(self):
        self.post_vote(self.participant_a)
        response = self.client.get(f'/api/votes/current/?voting={self.voting.id}', HTTP_HOST='localhost')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['vote']['participant'], self.participant_a.id)

    def test_database_unique_constraint_blocks_duplicate_active_vote(self):
        Vote.objects.create(
            voting=self.voting,
            user=self.user,
            participant=self.participant_a,
            voter_fingerprint='77001112233',
            voter_ip='127.0.0.1',
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Vote.objects.create(
                    voting=self.voting,
                    user=self.user,
                    participant=self.participant_b,
                    voter_fingerprint='77001112233',
                    voter_ip='127.0.0.2',
                )


@override_settings(
    OTP_AUTH_ENABLED=True,
    OTP_SECRET='unit-test-otp-secret',
    OTP_CODE_LENGTH=6,
    OTP_TTL_SECONDS=300,
    OTP_MAX_ATTEMPTS=3,
    OTP_LOCKOUT_SECONDS=900,
    OTP_RESEND_COOLDOWN_SECONDS=0,
    OTP_PHONE_DAILY_LIMIT=100,
    OTP_IP_DAILY_LIMIT=100,
    MANAGER_OTP_ENABLED=True,
    MANAGER_AUTH_ENABLED=True,
    MANAGER_SESSION_TTL_SECONDS=28800,
    OTP_PURPOSE_MANAGER_LOGIN='manager_login',
)
class DeterministicOTPTests(APITestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.mobizon = DummyMobizonClient()
        self.service = OTPService(mobizon_client=self.mobizon)
        self.phone = normalize_phone('+7 (700) 123-45-67')

    def request(self):
        return self.factory.post(
            '/api/auth/otp/request/',
            HTTP_HOST='localhost',
            HTTP_USER_AGENT='otp-test',
            REMOTE_ADDR='127.0.0.1',
        )

    def authenticate(self, user):
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        return token

    def authenticate_manager_session(self, user):
        token = self.authenticate(user)
        ManagerAuthSession.objects.create(
            user=user,
            token=token,
            expires_at=timezone.now() + timedelta(hours=1),
            ip_address='127.0.0.1',
            user_agent='test',
        )
        return token

    def test_same_phone_formats_generate_same_otp(self):
        phones = [
            normalize_phone('+77001234567'),
            normalize_phone('87001234567'),
            normalize_phone('8 700 123 45 67'),
        ]

        codes = {self.service.generate_otp(phone) for phone in phones}

        self.assertEqual(len(codes), 1)

    def test_different_phones_generate_different_otps(self):
        first = self.service.generate_otp(normalize_phone('+77001234567'))
        second = self.service.generate_otp(normalize_phone('+77007654321'))

        self.assertNotEqual(first, second)
        self.assertRegex(first, r'^\d{6}$')
        self.assertRegex(second, r'^\d{6}$')

    def test_missing_otp_secret_is_rejected(self):
        with override_settings(OTP_SECRET=''):
            with self.assertRaises(ImproperlyConfigured):
                OTPService(mobizon_client=self.mobizon).generate_otp(self.phone)

    def test_request_otp_sends_deterministic_code_and_stores_hash_only(self):
        code = self.service.generate_otp(self.phone)

        challenge = self.service.request_otp(self.phone, self.request())

        self.assertEqual(self.mobizon.messages[0][0], self.phone)
        self.assertIn(code, self.mobizon.messages[0][1])
        self.assertNotEqual(challenge.otp_hash, code)
        self.assertEqual(challenge.status, OTPChallenge.STATUS_SENT)

    def test_verify_otp_accepts_deterministic_code(self):
        self.service.request_otp(self.phone, self.request())
        code = self.service.generate_otp(self.phone)

        token, user, challenge = self.service.verify_otp(self.phone, code)

        self.assertEqual(user.username, self.phone)
        self.assertTrue(token.key)
        self.assertEqual(challenge.status, OTPChallenge.STATUS_VERIFIED)

    def test_wrong_otp_increments_attempts_and_locks_challenge(self):
        self.service.request_otp(self.phone, self.request())

        for _attempt in range(3):
            with self.assertRaises(OTPVerificationError):
                self.service.verify_otp(self.phone, '000000')

        challenge = OTPChallenge.objects.get(phone=self.phone)
        self.assertEqual(challenge.attempt_count, 3)
        self.assertEqual(challenge.status, OTPChallenge.STATUS_LOCKED)
        self.assertIsNotNone(challenge.locked_until)
        self.assertIsNotNone(challenge.last_attempt_at)

        with self.assertRaises(OTPVerificationError):
            self.service.verify_otp(self.phone, self.service.generate_otp(self.phone))

    def test_manager_endpoint_requires_authentication(self):
        response = self.client.post(
            '/api/manager/otp/generate/',
            {'phone': '+77001234567'},
            format='json',
            HTTP_HOST='localhost',
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_manager_endpoint_rejects_non_staff_user(self):
        user = get_user_model().objects.create_user(username='regular-user')
        self.authenticate(user)

        response = self.client.post(
            '/api/manager/otp/generate/',
            {'phone': '+77001234567'},
            format='json',
            HTTP_HOST='localhost',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_endpoint_rejects_staff_token_without_manager_session(self):
        manager = get_user_model().objects.create_user(username='manager', is_staff=True)
        self.authenticate(manager)

        response = self.client.post(
            '/api/manager/otp/generate/',
            {'phone': '+77001234567'},
            format='json',
            HTTP_HOST='localhost',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_endpoint_returns_otp_creates_challenge_and_audit_log(self):
        manager = get_user_model().objects.create_user(username='manager', is_staff=True)
        self.authenticate_manager_session(manager)

        response = self.client.post(
            '/api/manager/otp/generate/',
            {'phone': '+7 (700) 123-45-67'},
            format='json',
            HTTP_HOST='localhost',
            HTTP_USER_AGENT='manager-test',
            REMOTE_ADDR='127.0.0.5',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['phone'], self.phone)
        self.assertEqual(response.data['otp'], self.service.generate_otp(self.phone))
        self.assertEqual(OTPChallenge.objects.filter(phone=self.phone, status=OTPChallenge.STATUS_SENT).count(), 1)

        audit_log = ManagerOTPAuditLog.objects.get()
        self.assertEqual(audit_log.manager_user, manager)
        self.assertEqual(audit_log.phone, self.phone)
        self.assertEqual(audit_log.result, ManagerOTPAuditLog.RESULT_SUCCESS)
        self.assertNotEqual(audit_log.error_reason, response.data['otp'])

        self.client.credentials()
        verify_response = self.client.post(
            '/api/auth/otp/verify/',
            {'phone': '+77001234567', 'code': response.data['otp']},
            format='json',
            HTTP_HOST='localhost',
        )
        self.assertEqual(verify_response.status_code, status.HTTP_200_OK)
        self.assertTrue(verify_response.data['token'])

    def test_manager_endpoint_writes_validation_error_audit_log(self):
        manager = get_user_model().objects.create_user(username='manager', is_staff=True)
        self.authenticate_manager_session(manager)

        response = self.client.post(
            '/api/manager/otp/generate/',
            {'phone': 'invalid'},
            format='json',
            HTTP_HOST='localhost',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        audit_log = ManagerOTPAuditLog.objects.get()
        self.assertEqual(audit_log.manager_user, manager)
        self.assertEqual(audit_log.result, ManagerOTPAuditLog.RESULT_VALIDATION_ERROR)
        self.assertEqual(audit_log.phone, '')

    def test_manager_endpoint_is_throttled(self):
        cache.clear()
        manager = get_user_model().objects.create_user(username='manager', is_staff=True)
        self.authenticate_manager_session(manager)

        with patch.dict(ScopedRateThrottle.THROTTLE_RATES, {'manager_otp_generate': '1/min'}, clear=False):
            first_response = self.client.post(
                '/api/manager/otp/generate/',
                {'phone': '+77001234567'},
                format='json',
                HTTP_HOST='localhost',
            )
            second_response = self.client.post(
                '/api/manager/otp/generate/',
                {'phone': '+77007654321'},
                format='json',
                HTTP_HOST='localhost',
            )

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(
            ManagerOTPAuditLog.objects.filter(result=ManagerOTPAuditLog.RESULT_RATE_LIMITED).count(),
            1,
        )

    @patch('authentication.otp.MobizonClient', DummyMobizonClient)
    def test_manager_auth_request_otp_accepts_staff_password_and_returns_ticket(self):
        get_user_model().objects.create_user(username=self.phone, password='manager-pass', is_staff=True)

        response = self.client.post(
            '/api/manager/auth/request-otp/',
            {'phone': '+7 (700) 123-45-67', 'password': 'manager-pass'},
            format='json',
            HTTP_HOST='localhost',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['detail'], 'OTP sent')
        self.assertTrue(response.data['ticket'])
        challenge = OTPChallenge.objects.get(phone=self.phone, purpose='manager_login')
        self.assertEqual(challenge.status, OTPChallenge.STATUS_SENT)
        self.assertIn('ticket_hash', challenge.metadata)
        self.assertNotEqual(challenge.metadata['ticket_hash'], response.data['ticket'])

    @patch('authentication.otp.MobizonClient', DummyMobizonClient)
    def test_manager_auth_request_otp_rejects_wrong_password_and_non_staff_generically(self):
        get_user_model().objects.create_user(username=self.phone, password='manager-pass', is_staff=True)
        get_user_model().objects.create_user(username='77007654321', password='manager-pass', is_staff=False)

        wrong_password_response = self.client.post(
            '/api/manager/auth/request-otp/',
            {'phone': '+7 (700) 123-45-67', 'password': 'wrong-pass'},
            format='json',
            HTTP_HOST='localhost',
        )
        non_staff_response = self.client.post(
            '/api/manager/auth/request-otp/',
            {'phone': '+77007654321', 'password': 'manager-pass'},
            format='json',
            HTTP_HOST='localhost',
        )

        self.assertEqual(wrong_password_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(non_staff_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(wrong_password_response.data, non_staff_response.data)

    @patch('authentication.otp.MobizonClient', DummyMobizonClient)
    def test_manager_auth_verify_creates_manager_session(self):
        manager = get_user_model().objects.create_user(username=self.phone, password='manager-pass', is_staff=True)
        request_response = self.client.post(
            '/api/manager/auth/request-otp/',
            {'phone': '+7 (700) 123-45-67', 'password': 'manager-pass'},
            format='json',
            HTTP_HOST='localhost',
        )
        code = self.service.generate_otp(self.phone)

        verify_response = self.client.post(
            '/api/manager/auth/verify/',
            {'phone': '+7 (700) 123-45-67', 'ticket': request_response.data['ticket'], 'code': code},
            format='json',
            HTTP_HOST='localhost',
        )

        self.assertEqual(verify_response.status_code, status.HTTP_200_OK)
        self.assertTrue(verify_response.data['token'])
        self.assertEqual(verify_response.data['user']['username'], self.phone)
        token = Token.objects.get(user=manager)
        self.assertTrue(ManagerAuthSession.objects.filter(user=manager, token=token, revoked_at__isnull=True).exists())

    @patch('authentication.otp.MobizonClient', DummyMobizonClient)
    def test_manager_auth_verify_rejects_wrong_ticket_and_locks_attempts(self):
        get_user_model().objects.create_user(username=self.phone, password='manager-pass', is_staff=True)
        self.client.post(
            '/api/manager/auth/request-otp/',
            {'phone': '+7 (700) 123-45-67', 'password': 'manager-pass'},
            format='json',
            HTTP_HOST='localhost',
        )
        code = self.service.generate_otp(self.phone)

        for _attempt in range(3):
            response = self.client.post(
                '/api/manager/auth/verify/',
                {'phone': '+7 (700) 123-45-67', 'ticket': 'wrong-ticket', 'code': code},
                format='json',
                HTTP_HOST='localhost',
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        challenge = OTPChallenge.objects.get(phone=self.phone, purpose='manager_login')
        self.assertEqual(challenge.status, OTPChallenge.STATUS_LOCKED)
        self.assertIsNotNone(challenge.locked_until)

    def test_manager_auth_me_requires_active_manager_session(self):
        manager = get_user_model().objects.create_user(username=self.phone, is_staff=True)
        self.authenticate(manager)

        response_without_session = self.client.get('/api/manager/auth/me/', HTTP_HOST='localhost')
        self.assertEqual(response_without_session.status_code, status.HTTP_403_FORBIDDEN)

        token = Token.objects.get(user=manager)
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
        self.assertEqual(active_response.data['username'], self.phone)
