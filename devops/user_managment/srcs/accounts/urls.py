from django.urls import path, include, re_path
# from django.conf.urls import url
from accounts import views
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.routers import DefaultRouter
router = DefaultRouter()
router.register('profiles', views.ProfileViewSet, basename='profile')
# router.register('register')
urlpatterns = [
    # path('api-auth/', include('rest_framework.urls')),
    # path('api-auth/register/', views.UserRegistrationView.as_view(), name='register'),
    re_path(r'', include(router.urls)),
    path('login/', views.login),
    path('signup/', views.signup),
    path('test_token/', views.test_token),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('oauth2/login/', views.oauth2_login, name='oauth2_login'),
    path('oauth2/callback/', views.oauth2_callback, name='oauth2_callback'),
]
