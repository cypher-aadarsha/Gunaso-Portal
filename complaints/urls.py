from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router to automatically generate URLs for our ViewSets
router = DefaultRouter()
router.register(r'complaints', views.ComplaintViewSet, basename='complaint')
router.register(r'ministries', views.MinistryViewSet, basename='ministry')
router.register(r'departments', views.DepartmentViewSet, basename='department')
router.register(r'updates', views.ComplaintUpdateViewSet, basename='complaintupdate')
router.register(r'users', views.UserViewSet, basename='user')

# The API URLs are determined automatically by the router.
urlpatterns = [
    # All the router-generated URLs (e.g., /api/complaints/, /api/users/me/)
    path('', include(router.urls)),

    # The custom URL for registration
    path('register/', views.RegisterView.as_view(), name='register'),
]