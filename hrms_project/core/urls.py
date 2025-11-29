from rest_framework import routers
from django.urls import path, include
from . import views

router = routers.DefaultRouter()
router.register(r'categories', views.CategoryViewSet)
router.register(r'employees', views.EmployeeViewSet)
router.register(r'leaves', views.LeaveViewSet)
router.register(r'payrolls', views.PayrollViewSet)
router.register(r'replacement-requests', views.ReplacementRequestViewSet)
router.register(r'suggested-replacements', views.SuggestedReplacementViewSet)
router.register(r'competencies', views.CompetencyViewSet)
router.register(r'employee-competencies', views.EmployeeCompetencyViewSet)
router.register(r'performance-reviews', views.PerformanceReviewViewSet)
router.register(r'training-suggestions', views.TrainingSuggestionViewSet)
router.register(r'messages', views.MessageViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # statistics endpoints
    path('stats/workforce-by-gender/', views.stats_workforce_by_gender, name='stats_workforce_by_gender'),
    path('stats/avg-age/', views.stats_avg_age, name='stats_avg_age'),
    path('stats/avg-seniority/', views.stats_avg_seniority, name='stats_avg_seniority'),
    path('stats/turnover/', views.stats_turnover, name='stats_turnover'),
    path('stats/absenteeism-monthly/', views.stats_absenteeism_monthly, name='stats_absenteeism_monthly'),
    path('stats/unused-leave-summary/', views.stats_unused_leave_summary, name='stats_unused_leave_summary'),
    # employees with latest payroll
    path('employees-with-payments/', views.employees_with_payments, name='employees_with_payments'),
    # leave approval UI
    path('leaves/<int:pk>/approval/', views.leave_approval_page, name='leave_approval_page'),
    path('leaves/<int:pk>/approve/', views.approve_leave, name='approve_leave'),
    # chatbot FAQ endpoint (POST question -> JSON answer)
    path('chatbot/', views.chatbot_view, name='chatbot'),
    # Reports API (JSON)
    path('reports/list/', views.ReportsListAPIView.as_view(), name='reports_api'),
    # planner / replacement API
    path('planner/suggest-replacement/', views.SuggestReplacementAPIView.as_view(), name='suggest_replacement'),
    path('competency/match/', views.MatchCandidatesAPIView.as_view(), name='match_candidates'),
    path('competency/cartography/', views.CompetencyCartographyAPIView.as_view(), name='competency_cartography'),
    path('competency/suggest-trainings/', views.GenerateTrainingSuggestionsAPIView.as_view(), name='generate_training_suggestions'),
    # Self-service API: current authenticated employee
    path('employees/me/', views.EmployeeSelfAPIView.as_view(), name='employee_self_api'),
    path('performance/run/', views.PerformanceRunAPIView.as_view(), name='performance_run'),
    # Messaging API for employees
    path('messages/inbox/', views.MessagesInboxAPIView.as_view(), name='messages_inbox'),
    path('messages/send/', views.MessageSendAPIView.as_view(), name='messages_send'),
    path('messages/recipients/', views.MessageRecipientsAPIView.as_view(), name='messages_recipients'),
    path('planner/suggestions/<int:pk>/approve/', views.approve_suggestion, name='approve_suggestion'),
    path('planner/requests/create/', views.CreateReplacementRequestAPIView.as_view(), name='create_replacement_request'),
    path('employees/<int:pk>/leaves.ics', views.export_leaves_ical, name='employee_leaves_ical'),
    path('leaves.ics', views.export_leaves_ical, name='all_leaves_ical'),
]
