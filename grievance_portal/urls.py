"""
Main URL configuration for the grievance_portal project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings  # Import settings
from django.conf.urls.static import static  # Import static

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    # 1. Admin Panel
    path('admin/', admin.site.urls),

    # 2. API URLs
    path('api/', include('complaints.urls')),

    # 3. JWT Token Authentication
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # 4. API Auth (Browsing)
    path('api-auth/', include('rest_framework.urls')),
]

# --- THE FIX: Serve user-uploaded media files in development ---
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)