from django.urls import path
from rest_framework.routers import DefaultRouter

from tenancies.views import HomeView, TenancyExportView, TenancyViewSet, TenantInviteView

router = DefaultRouter()
router.register('tenancies', TenancyViewSet, basename='tenancy')

urlpatterns = [
    path('home/', HomeView.as_view(), name='home'),
    path('tenancies/<uuid:tenancy_id>/export/', TenancyExportView.as_view(), name='tenancy-export'),
    path('tenants/<uuid:tenant_id>/invite/', TenantInviteView.as_view(), name='tenant-invite'),
    *router.urls,
]
