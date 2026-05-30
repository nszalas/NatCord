from django.urls import path

from .views import report_list, report_state, report_user, update_report_status

urlpatterns = [
    path('reports/', report_list, name='report_list'),
    path('reports/state/', report_state, name='report_state'),
    path('reports/<int:report_id>/status/', update_report_status, name='update_report_status'),
    path('users/<int:user_id>/report/', report_user, name='report_user'),
]
