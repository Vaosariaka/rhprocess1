from django.urls import path
from .views import (
    home,
    rh_dashboard_view,
    rh_dashboard_state_view,
    EmployeeListView, EmployeeDetailView, LeaveListView,
    EmployeeCreateView, EmployeeUpdateView, EmployeeDeleteView,
    LeaveCreateView, LeaveUpdateView, LeaveDeleteView,
    export_employees_xlsx, export_leaves_xlsx,
    import_payroll_upload,
    export_employee_fiche, export_all_fiches, export_payroll_pdf,
    export_contract_pdf,
    planner_calendar,
    suggest_replacement_page,
    stats_charts,
    messages_page,
    performance_page,
    training_page,
    competency_cartography_page,
    match_candidates_page,
    reports_page,
    report_download,
    self_service_profile,
    employee_contract_action,
)

urlpatterns = [
    path('', home, name='home'),
    path('rh/dashboard/', rh_dashboard_view, name='rh_dashboard'),
    path('rh/dashboard/status/<str:state>/', rh_dashboard_state_view, name='rh_dashboard_state'),
    path('employees/', EmployeeListView.as_view(), name='employee_list'),
    path('employees/<int:pk>/', EmployeeDetailView.as_view(), name='employee_detail'),
    path('employees/add/', EmployeeCreateView.as_view(), name='employee_add'),
    path('employees/<int:pk>/edit/', EmployeeUpdateView.as_view(), name='employee_edit'),
    path('employees/<int:pk>/delete/', EmployeeDeleteView.as_view(), name='employee_delete'),
    path('employees/<int:pk>/action/<str:action>/', employee_contract_action, name='employee_contract_action'),

    path('leaves/', LeaveListView.as_view(), name='leave_list'),
    path('leaves/add/', LeaveCreateView.as_view(), name='leave_add'),
    path('leaves/<int:pk>/edit/', LeaveUpdateView.as_view(), name='leave_edit'),
    path('leaves/<int:pk>/delete/', LeaveDeleteView.as_view(), name='leave_delete'),
    # exports
    path('export/employees/', export_employees_xlsx, name='export_employees'),
    path('core/export_employees_xlsx/', export_employees_xlsx, name='legacy_export_employees'),
    path('export/leaves/', export_leaves_xlsx, name='export_leaves'),
    path('import/payroll/', import_payroll_upload, name='import_payroll_upload'),
    path('core/import_payroll/', import_payroll_upload, name='legacy_import_payroll'),
    path('export/fiche/<int:pk>/', export_employee_fiche, name='export_employee_fiche'),
    path('export/fiche/all/', export_all_fiches, name='export_all_fiches'),
    # PDF export for a specific payroll (payroll PK) - tries to render a PDF, falls back to XLSX
    path('export/payroll/<int:pk>/pdf/', export_payroll_pdf, name='export_payroll_pdf'),
    path('export/contract/<int:pk>/pdf/', export_contract_pdf, name='export_contract_pdf'),
    # Planner / auxiliary UI pages
    path('planner/calendar/', planner_calendar, name='planner_calendar'),
    path('planner/suggest/', suggest_replacement_page, name='planner_suggest'),
    path('planner/stats/', stats_charts, name='planner_stats'),
    path('planner/messages/', messages_page, name='planner_messages'),
    path('planner/performance/', performance_page, name='planner_performance'),
    path('planner/training/', training_page, name='planner_training'),
    # Competency UI
    path('competency/cartography/', competency_cartography_page, name='competency_cartography_page'),
    path('competency/match/', match_candidates_page, name='match_candidates_page'),
    # Reports UI
    path('reports/', reports_page, name='reports_page'),
    path('reports/download/<int:pk>/', report_download, name='report_download'),
    # Self-service profile
    path('employees/self-service/profile/', self_service_profile, name='self_service_profile'),
]
