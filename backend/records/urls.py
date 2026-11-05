from django.urls import path

from records.views import (
    ApplyRentIncreaseView,
    InviteMaintenanceView,
    InviteMessageView,
    MaintenanceRequestDetailView,
    MaintenanceRequestListView,
    MaintenanceTaskDoneView,
    MessageListView,
    NoticeCatalogView,
    NoticeListView,
    NoticePdfView,
    PacketView,
    RentPaymentListView,
    RentReceiptView,
)

urlpatterns = [
    path('notice-options/', NoticeCatalogView.as_view(), name='notice-options'),
    path('tenancies/<uuid:tenancy_id>/payments/', RentPaymentListView.as_view(), name='rent-payments'),
    path('tenancies/<uuid:tenancy_id>/payments/<uuid:payment_id>/receipt.pdf', RentReceiptView.as_view(), name='rent-receipt'),
    path('tenancies/<uuid:tenancy_id>/notices/', NoticeListView.as_view(), name='notices'),
    path('tenancies/<uuid:tenancy_id>/notices/<uuid:notice_id>/pdf/', NoticePdfView.as_view(), name='notice-pdf'),
    path('tenancies/<uuid:tenancy_id>/notices/<uuid:notice_id>/apply/', ApplyRentIncreaseView.as_view(), name='notice-apply'),
    path('tenancies/<uuid:tenancy_id>/messages/', MessageListView.as_view(), name='messages'),
    path('tenancies/<uuid:tenancy_id>/packet.pdf', PacketView.as_view(), name='packet'),
    path('units/<uuid:unit_id>/requests/', MaintenanceRequestListView.as_view(), name='maintenance-requests'),
    path('maintenance-requests/<uuid:request_id>/', MaintenanceRequestDetailView.as_view(), name='maintenance-request'),
    path('maintenance-tasks/<uuid:task_id>/done/', MaintenanceTaskDoneView.as_view(), name='maintenance-done'),
    path('invite/<str:token>/messages/', InviteMessageView.as_view(), name='invite-message'),
    path('invite/<str:token>/requests/', InviteMaintenanceView.as_view(), name='invite-request'),
]
