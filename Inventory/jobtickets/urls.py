from django.urls import path
from .views import (
    JobTicketDashboardView,
    CreateJobTicketView,
    EditJobTicketView,
    DeleteJobTicketView,
    GetSubmissionTokenView
    # Future: AddPartView, DeleteJobTicketView
)

urlpatterns = [
    path('', JobTicketDashboardView.as_view(), name='jobticket-dashboard'),
    path('create/', CreateJobTicketView.as_view(), name='create-jobticket'),
    path('<int:pk>/edit/', EditJobTicketView.as_view(), name='edit-jobticket'),
    # path('<int:pk>/add-part/', AddPartView.as_view(), name='add-part'),
    path('<int:pk>/delete/', DeleteJobTicketView.as_view(), name='delete-jobticket'),
    path('get-token/', GetSubmissionTokenView.as_view(), name='get-submission-token'),
]