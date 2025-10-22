"""
Main URL configuration for the grievance_portal project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # 1. The Django admin site (e.g., /admin/)
    path('admin/', admin.site.urls),

    # 2. Your API endpoints
    # This is the most important line. It tells Django:
    # "For any URL that starts with 'api/', go look at the
    # 'complaints.urls' file for more instructions."
    path('api/', include('complaints.urls')),

    # You can add other paths here later, e.g., for your frontend
    # path('', include('frontend.urls')),
]

# This is a helper for development.
# It tells Django to serve user-uploaded files (like documents)
# from your MEDIA_ROOT folder when you are in DEBUG mode.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)