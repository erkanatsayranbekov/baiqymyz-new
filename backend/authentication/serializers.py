import re

from django.conf import settings

from .models import CustomUser, Participant, Vote, Voting
from rest_framework import serializers


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['phone_number']


class RegisterSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=32)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    def validate_phone_number(self, value):
        return normalize_phone(value)


class VotingSerializer(serializers.ModelSerializer):
    is_active = serializers.SerializerMethodField()

    class Meta:
        model = Voting
        fields = ['id', 'title', 'status', 'starts_at', 'ends_at', 'is_active']

    def get_is_active(self, obj):
        return obj.is_active()


class ParticipantSerializer(serializers.ModelSerializer):
    avg_score = serializers.SerializerMethodField()
    vote_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Participant
        fields = ['id', 'voting', 'name', 'avg_score', 'vote_count', 'image', 'location']

    def get_avg_score(self, obj):
        return None


class VoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vote
        fields = [
            'id', 'voting', 'participant', 'user', 'score', 'voter_fingerprint',
            'voter_ip', 'latitude', 'longitude', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'score', 'voter_fingerprint', 'voter_ip',
            'latitude', 'longitude', 'created_at', 'updated_at'
        ]


class VoteCreateSerializer(serializers.Serializer):
    voting = serializers.PrimaryKeyRelatedField(queryset=Voting.objects.all())
    participant = serializers.PrimaryKeyRelatedField(queryset=Participant.objects.all())
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)


def normalize_phone(value):
    digits = re.sub(r'\D', '', value or '')
    if len(digits) == 10:
        digits = f'7{digits}'
    elif len(digits) == 11 and digits.startswith('8'):
        digits = f'7{digits[1:]}'

    if len(digits) != 11 or not digits.startswith('7'):
        raise serializers.ValidationError('Phone number must be in Kazakhstan international format.')

    return digits


class OTPRequestSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=32)

    def validate_phone(self, value):
        return normalize_phone(value)


class OTPVerifySerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=32)
    code = serializers.CharField(max_length=8)

    def validate_phone(self, value):
        return normalize_phone(value)

    def validate_code(self, value):
        if not value.isdigit() or len(value) != settings.OTP_CODE_LENGTH:
            raise serializers.ValidationError(f'OTP code must be exactly {settings.OTP_CODE_LENGTH} digits.')
        return value


class ManagerOTPGenerateSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=32)

    def validate_phone(self, value):
        return normalize_phone(value)


class ManagerAuthRequestOTPSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=32)
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_phone(self, value):
        return normalize_phone(value)


class ManagerAuthVerifySerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=32)
    ticket = serializers.CharField(max_length=255)
    code = serializers.CharField(max_length=8)

    def validate_phone(self, value):
        return normalize_phone(value)

    def validate_code(self, value):
        if not value.isdigit() or len(value) != settings.OTP_CODE_LENGTH:
            raise serializers.ValidationError(f'OTP code must be exactly {settings.OTP_CODE_LENGTH} digits.')
        return value
