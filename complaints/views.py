from django.contrib.auth.models import User
from rest_framework import viewsets, permissions, generics, status
from rest_framework.response import Response
from rest_framework.decorators import action

# Import all models and serializers
from .models import Ministry, Department, Complaint, ComplaintUpdate, UserProfile
from .serializers import (
    MinistrySerializer,
    DepartmentSerializer,
    ComplaintSerializer,
    ComplaintUpdateSerializer,
    RegisterSerializer,
    UserProfileSerializer
)
from .permissions import IsOwnerOrAdmin, IsMinistryAdmin, IsCitizen


# --- Auth Views ---

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    API endpoint to get AND update the profile for the logged-in user.
    Accessed at /api/profile/
    """
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user.profile


# --- Model ViewSets ---

class MinistryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ministry.objects.all().order_by('name')
    serializer_class = MinistrySerializer
    permission_classes = [permissions.AllowAny]


class DepartmentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = Department.objects.all().order_by('name')
        ministry_id = self.request.query_params.get('ministry_id')
        if ministry_id:
            queryset = queryset.filter(ministry_id=ministry_id)
        return queryset


class ComplaintViewSet(viewsets.ModelViewSet):
    queryset = Complaint.objects.all()
    serializer_class = ComplaintSerializer

    # FIXED: Permission now allows Owner OR Ministry Admin to access/edit
    permission_classes = [permissions.IsAuthenticated, (IsOwnerOrAdmin | IsMinistryAdmin)]

    lookup_field = 'tracking_id'

    def get_queryset(self):
        user = self.request.user
        # Super Admin
        if user.is_superuser or (hasattr(user, 'profile') and user.profile.role == 'SUPER'):
            return Complaint.objects.all().order_by('-created_at')

        # Ministry Admin
        if hasattr(user, 'profile') and user.profile.role == 'ADMIN':
            try:
                profile = user.profile
                if profile.department:
                    return Complaint.objects.filter(department=profile.department).order_by('-created_at')
                elif profile.ministry:
                    return Complaint.objects.filter(ministry=profile.ministry).order_by('-created_at')
            except UserProfile.DoesNotExist:
                return Complaint.objects.none()

        # Citizen (Default)
        return Complaint.objects.filter(created_by=user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Returns counts of complaints by status.
        URL: /api/complaints/stats/
        """
        queryset = self.filter_queryset(self.get_queryset())

        total = queryset.count()
        pending = queryset.filter(status='PENDING').count()
        in_progress = queryset.filter(status='IN_PROGRESS').count()
        resolved = queryset.filter(status='RESOLVED').count()
        rejected = queryset.filter(status='REJECTED').count()

        return Response({
            'total': total,
            'pending': pending,
            'in_progress': in_progress,
            'resolved': resolved,
            'rejected': rejected
        })


class ComplaintUpdateViewSet(viewsets.ModelViewSet):
    queryset = ComplaintUpdate.objects.all().order_by('-created_at')
    serializer_class = ComplaintUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        complaint_tracking_id = self.request.query_params.get('complaint_id')
        if complaint_tracking_id:
            return ComplaintUpdate.objects.filter(complaint__tracking_id=complaint_tracking_id)
        return ComplaintUpdate.objects.none()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)