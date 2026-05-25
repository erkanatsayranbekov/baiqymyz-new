from django.contrib import admin
from .models import CustomUser, ManagerAuthSession, ManagerOTPAuditLog, Participant, Vote, VoteHistory, Voting

# Register your models here.
admin.site.register(CustomUser)
admin.site.register(Voting)
admin.site.register(Participant)
admin.site.register(Vote)
admin.site.register(VoteHistory)
admin.site.register(ManagerOTPAuditLog)
admin.site.register(ManagerAuthSession)
