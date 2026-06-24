from django.contrib import admin
from .models import (
    AuthAuditLog,
    CustomUser,
    DeviceFingerprintBinding,
    DeviceObservation,
    ManagerAuthSession,
    ManagerOTPAuditLog,
    Participant,
    RiskEvent,
    Vote,
    VoteHistory,
    VoterDevice,
    VoterProfile,
    VoterSession,
    Voting,
)

# Register your models here.
admin.site.register(CustomUser)
admin.site.register(Voting)
admin.site.register(Participant)
admin.site.register(Vote)
admin.site.register(VoteHistory)
admin.site.register(ManagerOTPAuditLog)
admin.site.register(ManagerAuthSession)
admin.site.register(VoterProfile)
admin.site.register(VoterDevice)
admin.site.register(VoterSession)
admin.site.register(DeviceObservation)
admin.site.register(DeviceFingerprintBinding)
admin.site.register(RiskEvent)
admin.site.register(AuthAuditLog)
