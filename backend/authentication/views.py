from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from .serializers import (
    ManagerAuthRequestOTPSerializer,
    ManagerAuthVerifySerializer,
    ManagerOTPGenerateSerializer,
    OTPRequestSerializer,
    OTPVerifySerializer,
    VotingSerializer,
    UserSerializer,
    RegisterSerializer,
    ParticipantSerializer,
    VoteCreateSerializer,
    VoteSerializer,
)
from .models import CustomUser, ManagerAuthSession, ManagerOTPAuditLog, Participant, Vote, VoteHistory, Voting
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework import generics, mixins, status
from rest_framework.permissions import AllowAny, BasePermission, IsAdminUser, IsAuthenticated
import logging
import math
from datetime import timedelta
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.core.files.storage import default_storage
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.utils import timezone
from .otp import (
    OTPDeliveryError,
    OTPDisabledError,
    OTPRateLimitedError,
    OTPService,
    OTPVerificationError,
    build_vote_cookie,
    get_client_ip,
)

logger = logging.getLogger(__name__)


def calculate_distance_meters(lat1, lon1, lat2, lon2):
    earth_radius_meters = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    haversine = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return earth_radius_meters * 2 * math.atan2(math.sqrt(haversine), math.sqrt(1 - haversine))


def validate_vote_location(latitude, longitude):
    distance = calculate_distance_meters(
        latitude,
        longitude,
        settings.EVENT_LATITUDE,
        settings.EVENT_LONGITUDE,
    )
    return distance <= settings.EVENT_VOTE_RADIUS_METERS, distance


class IsStaffOrSuperuser(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_staff or request.user.is_superuser)
        )


class IsActiveManagerSession(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if not (request.user.is_staff or request.user.is_superuser):
            return False
        token = getattr(request, 'auth', None)
        if not token:
            return False

        session = (
            ManagerAuthSession.objects.filter(
                user=request.user,
                token=token,
                revoked_at__isnull=True,
                expires_at__gt=timezone.now(),
            )
            .order_by('-created_at')
            .first()
        )
        if not session:
            return False

        session.last_seen_at = timezone.now()
        session.save(update_fields=['last_seen_at'])
        request.manager_auth_session = session
        return True


def audit_manager_otp_request(request, phone='', result=ManagerOTPAuditLog.RESULT_SUCCESS, error_reason=''):
    user = request.user if request.user and request.user.is_authenticated else None
    ManagerOTPAuditLog.objects.create(
        manager_user=user,
        phone=phone,
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:2000],
        result=result,
        error_reason=error_reason[:255],
    )


def manager_user_payload(user):
    return {
        'id': user.id,
        'username': user.get_username(),
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
    }


def active_votings():
    now = timezone.now()
    return (
        Voting.objects.filter(status=Voting.STATUS_ACTIVE)
        .filter(Q(starts_at__isnull=True) | Q(starts_at__lte=now))
        .filter(Q(ends_at__isnull=True) | Q(ends_at__gte=now))
    )


def get_current_voting():
    return active_votings().order_by('-created_at').first()


def get_requested_or_current_voting(request):
    voting_id = request.query_params.get('voting')
    if voting_id:
        return get_object_or_404(Voting, id=voting_id)
    voting = get_current_voting()
    if not voting:
        return None
    return voting


def participant_image_url(participant, request=None):
    if not participant.image:
        return ''
    if participant.image.name and not default_storage.exists(participant.image.name):
        return ''
    try:
        url = participant.image.url
    except ValueError:
        return ''
    if request:
        return request.build_absolute_uri(url)
    return url


def build_voting_results(voting, request=None):
    user = request.user if request else None
    current_vote = None
    current_participant_id = None
    if user and user.is_authenticated:
        current_vote = (
            Vote.objects.filter(voting=voting, user=user)
            .select_related('participant')
            .first()
        )
        current_participant_id = current_vote.participant_id if current_vote else None

    participants = list(
        voting.participants.annotate(
            vote_count=Count(
                'votes',
                filter=Q(votes__voting=voting, votes__user__isnull=False),
                distinct=True,
            )
        ).order_by('-vote_count', 'name')
    )
    total_votes = sum((participant.vote_count or 0) for participant in participants)
    max_votes = max([participant.vote_count or 0 for participant in participants], default=0)

    candidates = []
    leaders = []
    for participant in participants:
        vote_count = participant.vote_count or 0
        percentage = round((vote_count / total_votes) * 100, 2) if total_votes else 0
        candidate = {
            'id': participant.id,
            'name': participant.name,
            'image': participant_image_url(participant, request),
            'location': participant.location,
            'vote_count': vote_count,
            'percentage': percentage,
            'is_user_vote': participant.id == current_participant_id,
        }
        candidates.append(candidate)
        if total_votes and vote_count == max_votes:
            leaders.append(candidate)

    return {
        'voting': VotingSerializer(voting).data,
        'total_votes': total_votes,
        'current_vote': {
            'id': current_vote.id,
            'participant': current_vote.participant_id,
        } if current_vote else None,
        'leaders': leaders,
        'candidates': candidates,
    }


class VotingViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Voting.objects.all().order_by('-created_at')
    serializer_class = VotingSerializer
    permission_classes = [AllowAny]

    @action(detail=False, methods=['get'])
    def current(self, request):
        voting = get_current_voting()
        if not voting:
            return Response({'detail': 'No active voting.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(self.get_serializer(voting).data)

    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        voting = self.get_object()
        return Response(build_voting_results(voting, request))


class ParticipantViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Participant.objects.all() 
    serializer_class = ParticipantSerializer
    permission_classes = [AllowAny]

    def paginate_queryset(self, queryset):
        if settings.PARTICIPANTS_LEGACY_UNPAGINATED and 'page' not in self.request.query_params:
            return None
        return super().paginate_queryset(queryset)

    def get_queryset(self):
        voting_id = self.request.query_params.get('voting')
        voting = None
        if voting_id:
            voting = get_object_or_404(Voting, id=voting_id)
        else:
            voting = get_current_voting()

        queryset = Participant.objects.all()
        if voting:
            queryset = queryset.filter(voting=voting)

        queryset = queryset.annotate(
            vote_count=Count(
                'votes',
                filter=Q(votes__voting=voting, votes__user__isnull=False) if voting else Q(votes__user__isnull=False),
                distinct=True,
            )
        )

        sorted_param = self.request.query_params.get('sorted', '').lower()
        if sorted_param == 'true':
            return queryset.order_by('-vote_count', 'name')

        return queryset.order_by('name')

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        voting = instance.voting or get_current_voting()
        vote_count = instance.votes.filter(
            voting=voting,
            user__isnull=False,
        ).count() if voting else 0

        serializer = self.get_serializer(instance)
        data = serializer.data
        data['avg_score'] = None
        data['vote_count'] = vote_count
        return Response(data)


def create_vote_history(vote, previous_participant, new_participant, request):
    VoteHistory.objects.create(
        voting=vote.voting,
        user=vote.user,
        previous_participant=previous_participant,
        new_participant=new_participant,
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:2000],
        device_fingerprint=request.data.get('voter_fingerprint', '')[:255],
    )


def vote_response(vote, detail, changed, response_status):
    return Response(
        {
            'detail': detail,
            'changed': changed,
            'vote': {
                'id': vote.id,
                'voting': vote.voting_id,
                'participant': vote.participant_id,
            },
        },
        status=response_status,
    )


def update_existing_vote(vote, participant, latitude, longitude, request):
    if vote.participant_id == participant.id:
        vote.latitude = latitude
        vote.longitude = longitude
        vote.voter_ip = get_client_ip(request)
        vote.voter_fingerprint = getattr(vote.user, 'username', '') or str(vote.user_id)
        vote.save(update_fields=['latitude', 'longitude', 'voter_ip', 'voter_fingerprint', 'updated_at'])
        return vote_response(vote, 'Vote already recorded for this candidate.', False, status.HTTP_200_OK)

    previous_participant = vote.participant
    recent_change_count = VoteHistory.objects.filter(
        voting=vote.voting,
        user=vote.user,
        created_at__gte=timezone.now() - timedelta(minutes=10),
    ).count()
    if recent_change_count >= 5:
        logger.warning('Suspicious frequent vote changes user=%s voting=%s', vote.user_id, vote.voting_id)

    vote.participant = participant
    vote.voter_ip = get_client_ip(request)
    vote.voter_fingerprint = getattr(vote.user, 'username', '') or str(vote.user_id)
    vote.latitude = latitude
    vote.longitude = longitude
    vote.score = 1
    vote.save(update_fields=['participant', 'voter_ip', 'voter_fingerprint', 'latitude', 'longitude', 'score', 'updated_at'])
    create_vote_history(vote, previous_participant, participant, request)
    return vote_response(vote, 'Vote updated.', True, status.HTTP_200_OK)


def create_new_vote(voting, participant, user, latitude, longitude, request):
    vote = Vote.objects.create(
        voting=voting,
        user=user,
        participant=participant,
        score=1,
        voter_fingerprint=getattr(user, 'username', '') or str(user.id),
        voter_ip=get_client_ip(request),
        latitude=latitude,
        longitude=longitude,
    )
    create_vote_history(vote, None, participant, request)
    return vote_response(vote, 'Vote recorded.', True, status.HTTP_201_CREATED)


class VoteViewSet(viewsets.ModelViewSet):
    queryset = Vote.objects.all()
    serializer_class = VoteSerializer

    def get_permissions(self):
        if self.action in ['create', 'current']:
            return [IsAuthenticated()]
        if self.action in ['results', 'by_fingerprint']:
            return [AllowAny()]
        return [IsAdminUser()]

    def get_throttles(self):
        if self.action == 'create':
            self.throttle_scope = 'vote_create'
        elif self.action in ['by_fingerprint', 'current', 'results']:
            self.throttle_scope = 'vote_lookup'
        return super().get_throttles()

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = VoteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        voting = serializer.validated_data['voting']
        participant = serializer.validated_data['participant']
        latitude = serializer.validated_data['latitude']
        longitude = serializer.validated_data['longitude']

        if not voting.is_active():
            logger.warning('Vote attempt in inactive voting user=%s voting=%s', request.user.id, voting.id)
            return Response({'detail': 'Voting is not active.'}, status=status.HTTP_403_FORBIDDEN)

        if participant.voting_id != voting.id:
            logger.warning(
                'Vote participant mismatch user=%s voting=%s participant=%s',
                request.user.id,
                voting.id,
                participant.id,
            )
            return Response({'detail': 'Candidate does not belong to this voting.'}, status=status.HTTP_400_BAD_REQUEST)

        is_inside_event, distance = validate_vote_location(latitude, longitude)
        if not is_inside_event:
            logger.warning(
                'Vote outside event radius user=%s voting=%s distance_meters=%.2f',
                request.user.id,
                voting.id,
                distance,
            )
            return Response(
                {'detail': 'Voting is only available at the event location.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        existing_vote = (
            Vote.objects.select_for_update()
            .filter(voting=voting, user=request.user)
            .select_related('participant')
            .first()
        )

        if existing_vote:
            return update_existing_vote(existing_vote, participant, latitude, longitude, request)

        try:
            with transaction.atomic():
                return create_new_vote(voting, participant, request.user, latitude, longitude, request)
        except IntegrityError:
            existing_vote = (
                Vote.objects.select_for_update()
                .filter(voting=voting, user=request.user)
                .select_related('participant')
                .get()
            )
            return update_existing_vote(existing_vote, participant, latitude, longitude, request)

    @action(detail=False, methods=['get'])
    def by_fingerprint(self, request):
        return Response(
            {'detail': 'This endpoint is deprecated. Use /api/votes/current/?voting=<id>.'},
            status=status.HTTP_410_GONE,
        )

    @action(detail=False, methods=['get'])
    def current(self, request):
        voting = get_requested_or_current_voting(request)
        if not voting:
            return Response({'detail': 'No active voting.'}, status=status.HTTP_404_NOT_FOUND)

        vote = Vote.objects.filter(voting=voting, user=request.user).first()
        if not vote:
            return Response({'voting': voting.id, 'vote': None})

        return Response({
            'voting': voting.id,
            'vote': {
                'id': vote.id,
                'participant': vote.participant_id,
            },
        })

    @action(detail=False, methods=['get'])
    def results(self, request):
        voting = get_requested_or_current_voting(request)
        if not voting:
            return Response({'detail': 'No active voting.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(build_voting_results(voting, request))


class UserViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]


class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer
    throttle_scope = 'register'

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone_number"]

        if settings.OTP_AUTH_ENABLED:
            try:
                OTPService().request_otp(phone, request)
            except OTPRateLimitedError:
                return Response({'detail': 'Too many OTP requests.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)
            except OTPDeliveryError:
                return Response({'detail': 'OTP could not be sent.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

            return Response({"detail": "OTP sent"}, status=status.HTTP_200_OK)

        if not settings.LEGACY_PASSWORD_AUTH_ENABLED:
            return Response({"detail": "Legacy password auth is disabled."}, status=status.HTTP_410_GONE)

        password = serializer.validated_data.get("password")

        if not password:
            return Response({"detail": "Номер телефона и пароль обязательны."}, status=status.HTTP_400_BAD_REQUEST)

        user, created = CustomUser.objects.update_or_create(
            phone_number=phone,
            defaults={"password": password}
        )

        unique_hash = build_vote_cookie(phone)

        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        response = Response(
            {
                "detail": "Пользователь создан или обновлён.",
                "phone_number": user.phone_number,
            },
            status=status_code,
        )
        
        response.set_cookie(
            key="x-unique-vote",
            value=unique_hash,
            httponly=True,
            secure=not settings.DEBUG,
            samesite="Lax",
            max_age=60 * 60 * 24 * 30,
        )

        return response



class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'login'

    def post(self, request):
        if not settings.LEGACY_PASSWORD_AUTH_ENABLED:
            return Response({"detail": "Legacy password auth is disabled."}, status=status.HTTP_410_GONE)

        phone = request.data.get("phone_number")
        password = request.data.get("password")

        if not phone or not password:
            return Response({"detail": "Номер телефона и пароль обязательны."}, status=status.HTTP_400_BAD_REQUEST)

        user = get_object_or_404(CustomUser, phone_number=phone)

        if user.password != password:
            return Response({"detail": "Неверный пароль."}, status=status.HTTP_401_UNAUTHORIZED)

        return Response({"detail": "Успешный вход.", "phone_number": user.phone_number}, status=status.HTTP_200_OK)


class AuthMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {
                'id': request.user.id,
                'username': request.user.get_username(),
                'is_staff': request.user.is_staff,
                'is_superuser': request.user.is_superuser,
            },
            status=status.HTTP_200_OK,
        )


class ManagerAuthRequestOTPView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'manager_login_request'

    def post(self, request):
        if not settings.MANAGER_AUTH_ENABLED or not settings.OTP_AUTH_ENABLED:
            return Response({'detail': 'Manager authentication is disabled.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        serializer = ManagerAuthRequestOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data['phone']
        password = serializer.validated_data['password']

        user = authenticate(request, username=phone, password=password)
        if not user or not user.is_active or not (user.is_staff or user.is_superuser):
            return Response({'detail': 'Invalid manager credentials.'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            ticket, _challenge = OTPService().request_manager_login_otp(phone, user, request)
        except OTPDisabledError:
            return Response({'detail': 'OTP authentication is disabled.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except OTPRateLimitedError:
            return Response({'detail': 'Too many OTP requests.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except OTPDeliveryError:
            return Response({'detail': 'OTP could not be sent.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response({'detail': 'OTP sent', 'ticket': ticket}, status=status.HTTP_200_OK)


class ManagerAuthVerifyView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'manager_login_verify'

    def post(self, request):
        if not settings.MANAGER_AUTH_ENABLED or not settings.OTP_AUTH_ENABLED:
            return Response({'detail': 'Manager authentication is disabled.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        serializer = ManagerAuthVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data['phone']

        try:
            challenge = OTPService().verify_manager_login_otp(
                phone,
                serializer.validated_data['ticket'],
                serializer.validated_data['code'],
            )
        except OTPDisabledError:
            return Response({'detail': 'OTP authentication is disabled.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except OTPVerificationError:
            return Response({'detail': 'Invalid or expired OTP.'}, status=status.HTTP_400_BAD_REQUEST)

        manager_user_id = challenge.metadata.get('manager_user_id')
        User = get_user_model()
        user = get_object_or_404(User, id=manager_user_id, username=phone)
        if not user.is_active or not (user.is_staff or user.is_superuser):
            return Response({'detail': 'Invalid manager credentials.'}, status=status.HTTP_401_UNAUTHORIZED)

        token, _created = Token.objects.get_or_create(user=user)
        expires_at = timezone.now() + timedelta(seconds=settings.MANAGER_SESSION_TTL_SECONDS)
        session = ManagerAuthSession.objects.create(
            user=user,
            token=token,
            expires_at=expires_at,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:2000],
        )

        return Response(
            {
                'token': token.key,
                'user': manager_user_payload(user),
                'expires_at': session.expires_at,
            },
            status=status.HTTP_200_OK,
        )


class ManagerAuthMeView(APIView):
    permission_classes = [IsActiveManagerSession]

    def get(self, request):
        session = request.manager_auth_session
        return Response(
            {
                **manager_user_payload(request.user),
                'manager_session_expires_at': session.expires_at,
            },
            status=status.HTTP_200_OK,
        )


class OTPRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'otp_request'

    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            OTPService().request_otp(serializer.validated_data['phone'], request)
        except OTPDisabledError:
            return Response({'detail': 'OTP authentication is disabled.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except OTPRateLimitedError:
            return Response({'detail': 'Too many OTP requests.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except OTPDeliveryError:
            return Response({'detail': 'OTP could not be sent.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response({'detail': 'OTP sent'}, status=status.HTTP_200_OK)


class ManagerOTPGenerateView(APIView):
    permission_classes = [IsActiveManagerSession]
    throttle_scope = 'manager_otp_generate'

    def throttled(self, request, wait):
        if request.user and request.user.is_authenticated:
            audit_manager_otp_request(
                request,
                result=ManagerOTPAuditLog.RESULT_RATE_LIMITED,
                error_reason='throttle_limit',
            )
        return super().throttled(request, wait)

    def post(self, request):
        if not settings.MANAGER_OTP_ENABLED or not settings.OTP_AUTH_ENABLED:
            audit_manager_otp_request(
                request,
                result=ManagerOTPAuditLog.RESULT_DISABLED,
                error_reason='manager_otp_disabled',
            )
            return Response({'detail': 'Manager OTP generation is disabled.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        serializer = ManagerOTPGenerateSerializer(data=request.data)
        if not serializer.is_valid():
            audit_manager_otp_request(
                request,
                result=ManagerOTPAuditLog.RESULT_VALIDATION_ERROR,
                error_reason='invalid_phone',
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        phone = serializer.validated_data['phone']
        otp_service = OTPService()
        code = otp_service.generate_otp(phone)
        otp_service.create_manager_challenge(phone, request)
        audit_manager_otp_request(request, phone=phone, result=ManagerOTPAuditLog.RESULT_SUCCESS)

        return Response(
            {
                'phone': phone,
                'otp': code,
            },
            status=status.HTTP_200_OK,
        )


class OTPVerifyView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'otp_verify'

    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data['phone']

        try:
            token, user, _challenge = OTPService().verify_otp(phone, serializer.validated_data['code'])
        except OTPDisabledError:
            return Response({'detail': 'OTP authentication is disabled.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except OTPVerificationError:
            return Response({'detail': 'Invalid or expired OTP.'}, status=status.HTTP_400_BAD_REQUEST)

        response = Response(
            {
                'token': token.key,
                'user': {
                    'id': user.id,
                    'phone_number': phone,
                },
            },
            status=status.HTTP_200_OK,
        )
        response.set_cookie(
            key="x-unique-vote",
            value=build_vote_cookie(phone),
            httponly=True,
            secure=not settings.DEBUG,
            samesite="Lax",
            max_age=60 * 60 * 24 * 30,
        )
        return response
