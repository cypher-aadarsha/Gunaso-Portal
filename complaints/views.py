from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.auth.models import User
from rest_framework.generics import CreateAPIView

# Import the correct models
from .models import Complaint, Ministry, Department, ComplaintUpdate, UserProfile

# Import the correct serializers from serializers.py
from .serializers import (
    ComplaintSerializer,
    MinistrySerializer,
    DepartmentSerializer,
    ComplaintUpdateSerializer,
    RegisterSerializer,
    UserSerializer
)


class RegisterView(CreateAPIView):
    """
    API endpoint for new citizen registration.
    """
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint to view user data.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def me(self, request):
        """
        A special endpoint to get the currently logged-in user's data.
        Access at /api/users/me/
        """
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class MinistryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint to list all Ministries.
    Access at /api/ministries/
    """
    queryset = Ministry.objects.all()
    serializer_class = MinistrySerializer
    permission_classes = [permissions.AllowAny]  # Everyone can see ministries


class DepartmentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint to list all Departments.
    Can be filtered by ministry_id.
    Access at /api/departments/ or /api/departments/?ministry_id=1
    """
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.AllowAny]  # Everyone can see departments

    def get_queryset(self):
        """
        Optionally filter the queryset by a 'ministry_id' URL parameter.
        """
        queryset = super().get_queryset()
        ministry_id = self.request.query_params.get('ministry_id')
        if ministry_id:
            queryset = queryset.filter(ministry_id=ministry_id)
        return queryset


class ComplaintViewSet(viewsets.ModelViewSet):
    """
    The main API endpoint for creating, listing, and retrieving complaints.
    Handles all the permission logic.
    """
    queryset = Complaint.objects.all()
    serializer_class = ComplaintSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'tracking_id'  # Use tracking_id in URL instead of pk

    def get_queryset(self):
        """
        This is the core security logic.
        - Super Admins see everything.
        - Staff Admins see only their ministry/department's complaints.
        - Citizens see only their own complaints.
        """
        user = self.request.user

        if user.is_superuser:
            # Super Admin: sees all complaints
            return Complaint.objects.all()

        if user.is_staff:
            # Admin Layer:
            try:
                profile = user.profile
                if profile.department:
                    # Dept admin: sees only their department's complaints
                    return Complaint.objects.filter(department=profile.department)
                elif profile.ministry:
                    # Ministry admin: sees all complaints for their ministry
                    return Complaint.objects.filter(ministry=profile.ministry)
                else:
                    # Unassigned staff: sees nothing
                    return Complaint.objects.none()
            except UserProfile.DoesNotExist:
                return Complaint.objects.none()  # Staff with no profile
        else:
            # Citizen Layer: sees only their own complaints
            return Complaint.objects.filter(created_by=user)

    def perform_create(self, serializer):
        """
        Automatically set the 'created_by' field to the current user
        when a new complaint is created.
        """
        # Check if this is the user's first complaint
        has_filed_before = Complaint.objects.filter(created_by=self.request.user).exists()

        if has_filed_before:
            # If they have, don't save the ID document again
            serializer.save(created_by=self.request.user, government_id_document=None)
        else:
            # This is their first complaint, save the ID document
            serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny],
            url_path='status/(?P<tracking_id>[0-9a-f-]+)')
    def get_status(self, request, tracking_id=None):
        """
        A public endpoint for anyone to check a complaint's status
        using its tracking ID.
        Access at /api/complaints/status/<uuid:tracking_id>/
        """
        try:
            complaint = Complaint.objects.get(tracking_id=tracking_id)
            data = {
                'tracking_id': complaint.tracking_id,
                'status': complaint.status,
                'title': complaint.title,
                'created_at': complaint.created_at,
                'updated_at': complaint.updated_at
            }
            return Response(data)
        except Complaint.DoesNotExist:
            return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)


class ComplaintUpdateViewSet(viewsets.ModelViewSet):
    """
    API endpoint for adding/viewing updates to a complaint.
    """
    queryset = ComplaintUpdate.objects.all()
    serializer_class = ComplaintUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Only show updates for a specific complaint,
        and one the user is allowed to see.
        """
        # We can implement full security later. For now, filter by complaint.
        complaint_tracking_id = self.request.query_params.get('complaint_id')
        if complaint_tracking_id:
            return ComplaintUpdate.objects.filter(complaint__tracking_id=complaint_tracking_id)
        return ComplaintUpdate.objects.none()  # Don't return all updates

    def perform_create(self, serializer):
        """
        Automatically set the user who made the update.
        """
        serializer.save(user=self.request.user)