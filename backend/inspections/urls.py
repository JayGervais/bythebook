from django.urls import path

from inspections.views import (
    InspectionCopyHandedView,
    InspectionDetailView,
    InspectionFinalizeView,
    InspectionPdfView,
    InspectionPhotoView,
    InspectionReviseView,
    InspectionSignatureView,
    InviteInspectionView,
    InvitePdfView,
    InviteSignView,
    PhotoDeleteView,
    TenancyInspectionCreateView,
)

urlpatterns = [
    path('tenancies/<uuid:tenancy_id>/inspections/', TenancyInspectionCreateView.as_view(), name='inspection-create'),
    path('inspections/<uuid:inspection_id>/', InspectionDetailView.as_view(), name='inspection-detail'),
    path('inspections/<uuid:inspection_id>/pdf/', InspectionPdfView.as_view(), name='inspection-pdf'),
    path('inspections/<uuid:inspection_id>/finalize/', InspectionFinalizeView.as_view(), name='inspection-finalize'),
    path('inspections/<uuid:inspection_id>/revise/', InspectionReviseView.as_view(), name='inspection-revise'),
    path('inspections/<uuid:inspection_id>/copy-handed/', InspectionCopyHandedView.as_view(), name='inspection-copy'),
    path('inspections/<uuid:inspection_id>/signatures/', InspectionSignatureView.as_view(), name='inspection-sign'),
    path('inspections/<uuid:inspection_id>/items/<uuid:item_id>/photos/', InspectionPhotoView.as_view(), name='inspection-photo'),
    path('photos/<uuid:photo_id>/', PhotoDeleteView.as_view(), name='photo-delete'),
    path('invite/<str:token>/', InviteInspectionView.as_view(), name='invite'),
    path('invite/<str:token>/sign/', InviteSignView.as_view(), name='invite-sign'),
    path('invite/<str:token>/inspections/<uuid:inspection_id>/pdf/', InvitePdfView.as_view(), name='invite-pdf'),
]
