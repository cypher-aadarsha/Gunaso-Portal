from django.contrib.auth.models import User
from rest_framework import viewsets, permissions, generics, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from django.db import transaction
import openpyxl

from .models import Ministry, Department, Complaint, ComplaintUpdate, UserProfile
from .serializers import (
    MinistrySerializer,
    DepartmentSerializer,
    ComplaintSerializer,
    ComplaintUpdateSerializer,
    RegisterSerializer,
    UserProfileSerializer,
    BulkAdminUploadSerializer
)
from .permissions import IsOwnerOrAdmin, IsMinistryAdmin, IsCitizen


# --- Auth Views ---

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer


class UserProfileView(generics.RetrieveUpdateAPIView):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user.profile


class BulkAdminCreateView(APIView):
    permission_classes = [permissions.IsAdminUser]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        serializer = BulkAdminUploadSerializer(data=request.data)
        if serializer.is_valid():
            file = request.FILES['file']
            try:
                workbook = openpyxl.load_workbook(file)
                sheet = workbook.active
                created_count = 0
                errors = []

                for index, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
                    if not row[0] or not row[2]:
                        continue

                    # Columns: 0:username, 1:email, 2:password, 3:first_name, 4:last_name,
                    # 5:phone_number, 6:ministry_name, 7:department_name
                    username, email, password, first_name, last_name, phone_number, ministry_name, department_name = row[
                        :8]

                    try:
                        with transaction.atomic():
                            if User.objects.filter(username=username).exists():
                                errors.append(f"Row {index}: Username '{username}' already exists.")
                                continue

                            user = User.objects.create_user(
                                username=username, email=email, password=password,
                                first_name=first_name, last_name=last_name
                            )
                            ministry_obj = Ministry.objects.filter(
                                name__iexact=ministry_name).first() if ministry_name else None
                            department_obj = Department.objects.filter(
                                name__iexact=department_name).first() if department_name else None

                            UserProfile.objects.create(
                                user=user, role='ADMIN', phone_number=phone_number,
                                ministry=ministry_obj, department=department_obj
                            )
                            created_count += 1
                    except Exception as e:
                        errors.append(f"Row {index}: Error creating user '{username}': {str(e)}")

                return Response({"message": f"Successfully created {created_count} admin accounts.", "errors": errors},
                                status=status.HTTP_200_OK)
            except Exception as e:
                return Response({"error": f"Failed to process file: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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

        # Updated to handle comma-separated list of ministry IDs (e.g. ?ministry_ids=1,2)
        ministry_ids_param = self.request.query_params.get('ministry_ids')
        if ministry_ids_param:
            ids = [int(id) for id in ministry_ids_param.split(',') if id.isdigit()]
            queryset = queryset.filter(ministry_id__in=ids)

        # Fallback for single ID legacy support
        ministry_id = self.request.query_params.get('ministry_id')
        if ministry_id:
            queryset = queryset.filter(ministry_id=ministry_id)

        return queryset


class ComplaintViewSet(viewsets.ModelViewSet):
    queryset = Complaint.objects.all()
    serializer_class = ComplaintSerializer
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
                # UPDATED: Check if the admin's department/ministry is in the complaint's list
                if profile.department:
                    return Complaint.objects.filter(departments=profile.department).order_by('-created_at').distinct()
                elif profile.ministry:
                    return Complaint.objects.filter(ministries=profile.ministry).order_by('-created_at').distinct()
            except UserProfile.DoesNotExist:
                return Complaint.objects.none()

        # Citizen (Default)
        return Complaint.objects.filter(created_by=user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        total = queryset.count()
        return Response({
            'total': total,
            'pending': queryset.filter(status='PENDING').count(),
            'in_progress': queryset.filter(status='IN_PROGRESS').count(),
            'resolved': queryset.filter(status='RESOLVED').count(),
            'rejected': queryset.filter(status='REJECTED').count()
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