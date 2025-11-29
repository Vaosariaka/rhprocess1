from rest_framework import serializers
from .models import (
    Category,
    Employee,
    Leave,
    Payroll,
    ReplacementRequest,
    SuggestedReplacement,
    Competency,
    PerformanceReview,
    TrainingSuggestion,
    Message,
    # EmployeeCompetency will be imported dynamically below if present
)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']


class EmployeeSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(write_only=True, source='category', queryset=Category.objects.all(), required=False, allow_null=True)

    class Meta:
        model = Employee
        fields = ['id', 'matricule', 'email', 'cnaps_number', 'first_name', 'last_name', 'category', 'category_id', 'function', 'hire_date', 'salary_base']


class LeaveSerializer(serializers.ModelSerializer):
    employee = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.all())

    class Meta:
        model = Leave
        fields = ['id', 'employee', 'start_date', 'end_date', 'leave_type', 'status', 'note', 'days']
        read_only_fields = ['days']


class PayrollSerializer(serializers.ModelSerializer):
    employee = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.all())

    class Meta:
        model = Payroll
        fields = ['id', 'employee', 'month', 'year', 'gross_salary', 'net_salary', 'created_at']
        read_only_fields = ['created_at']


class ReplacementRequestSerializer(serializers.ModelSerializer):
    target_employee = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.all())

    class Meta:
        model = ReplacementRequest
        fields = ['id', 'requester', 'target_employee', 'start_date', 'end_date', 'department_hint', 'function_hint', 'status', 'notes', 'created_at']
        read_only_fields = ['created_at']


class SuggestedReplacementSerializer(serializers.ModelSerializer):
    candidate = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.all())

    class Meta:
        model = SuggestedReplacement
        fields = ['id', 'request', 'candidate', 'score', 'note', 'approved', 'approved_by', 'approved_at', 'created_at']
        read_only_fields = ['created_at', 'approved_by', 'approved_at']


class CompetencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Competency
        fields = ['id', 'name', 'description']


class EmployeeCompetencySerializer(serializers.ModelSerializer):
    employee = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.all())
    competency = serializers.PrimaryKeyRelatedField(queryset=Competency.objects.all())

    class Meta:
        # import model by attribute to avoid circular import issues at module load
        from core.models import EmployeeCompetency

        model = EmployeeCompetency
        fields = ['id', 'employee', 'competency', 'level', 'last_used', 'created_at']
        read_only_fields = ['created_at']


class PerformanceReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = PerformanceReview
        fields = ['id', 'reviewer', 'employee', 'review_date', 'score', 'comments', 'created_at']
        read_only_fields = ['created_at']


class TrainingSuggestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingSuggestion
        fields = ['id', 'employee', 'competency', 'title', 'description', 'suggested_by', 'created_at']
        read_only_fields = ['created_at']


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['id', 'sender', 'recipient', 'subject', 'body', 'read', 'created_at']
        read_only_fields = ['created_at']


class EmployeeSelfSerializer(serializers.ModelSerializer):
    """Serializer for employees to update their own profile via API."""
    class Meta:
        model = Employee
        # allow employees to update contact and profile fields only
        fields = ['id', 'matricule', 'email', 'first_name', 'last_name', 'phone', 'address', 'department', 'function', 'photo', 'emergency_contact']
        read_only_fields = ['id', 'matricule', 'first_name', 'last_name']

