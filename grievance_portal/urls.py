"""
Main URL configuration for the grievance_portal project.
"""
from django.contrib import admin
from django.urls import path, include

# --- THIS IS THE FIX ---
# Import the JWT token views that were missing
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    # 1. Admin Panel
    path('admin/', admin.site.urls),

    # 2. API URLs
    # All URLs from the 'complaints' app will be prefixed with 'api/'
    # e.g., /api/complaints/, /api/register/, /api/profile/
    path('api/', include('complaints.urls')),

    # 3. Built-in JWT Token Authentication (THESE LINES WERE MISSING)
    # The login.html page will send its request to this URL
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # 4. API Auth (for login/logout buttons in browsable API)
    path('api-auth/', include('rest_framework.urls')),
]