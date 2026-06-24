from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from rest_framework import routers
from authentication import views

router = routers.SimpleRouter()
router.register(r'users', views.UserViewSet)
router.register(r'votings', views.VotingViewSet)
router.register(r'participants', views.ParticipantViewSet)
router.register(r'votes', views.VoteViewSet)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include([
        path('', include(router.urls)),
        path('auth/phone/', views.PhoneAuthView.as_view(), name='phone-auth'),
        path('auth/logout/', views.AuthLogoutView.as_view(), name='auth-logout'),
        path('auth/me/', views.AuthMeView.as_view(), name='auth-me'),
        path('auth/otp/request/', views.GoneOTPView.as_view(), name='otp-request'),
        path('auth/otp/verify/', views.GoneOTPView.as_view(), name='otp-verify'),
        path('manager/auth/login/', views.ManagerPasswordLoginView.as_view(), name='manager-auth-login'),
        path('manager/auth/request-otp/', views.GoneOTPView.as_view(), name='manager-auth-request-otp'),
        path('manager/auth/verify/', views.GoneOTPView.as_view(), name='manager-auth-verify'),
        path('manager/auth/me/', views.ManagerAuthMeView.as_view(), name='manager-auth-me'),
        path('manager/otp/generate/', views.GoneOTPView.as_view(), name='manager-otp-generate'),
        path('register/', views.PhoneAuthView.as_view(), name='register'),
        path('login/', views.LoginView.as_view(), name='login')
    ])),
]

if settings.SERVE_MEDIA_IN_DJANGO:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
