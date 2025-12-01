from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'complaints', views.ComplaintViewSet, basename='complaint')
router.register(r'ministries', views.MinistryViewSet, basename='ministry')
router.register(r'departments', views.DepartmentViewSet, basename='department')
router.register(r'complaint-updates', views.ComplaintUpdateViewSet, basename='complaintupdate')

# The API URLs are now determined automatically by the router.
# Additionally, we include the login URLs for the browsable API.
urlpatterns = [
    # All URLs from the router (e.g., /api/complaints/, /api/ministries/)
    path('', include(router.urls)),

    # Custom auth URLs
    path('register/', views.RegisterView.as_view(), name='register'),

    # New Profile URL
    path('profile/', views.UserProfileView.as_view(), name='user-profile'),
]