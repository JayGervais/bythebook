from django.urls import path
from rest_framework.routers import DefaultRouter

from tenancies.views import (
    HomeView,
    TenancyExportView,
    TenancyViewSet,
    TenantAccountLinkView,
    TenantAccountView,
    TenantHomeView,
    TenantInviteView,
    TenantJoinView,
    TenantMessageView,
)

router = DefaultRouter()
router.register('tenancies', TenancyViewSet, basename='tenancy')

urlpatterns = [
    path('home/', HomeView.as_view(), name='home'),
    path('tenant/home/', TenantHomeView.as_view(), name='tenant-home'),
    path('tenant/messages/', TenantMessageView.as_view(), name='tenant-messages'),
    path('tenancies/<uuid:tenancy_id>/export/', TenancyExportView.as_view(), name='tenancy-export'),
    path('tenancies/<uuid:tenancy_id>/tenants/', TenantAccountView.as_view(), name='tenant-account'),
    path('tenants/<uuid:tenant_id>/invite/', TenantInviteView.as_view(), name='tenant-invite'),
    path('tenants/<uuid:tenant_id>/account-link/', TenantAccountLinkView.as_view(), name='tenant-account-link'),
    path('join/<str:token>/', TenantJoinView.as_view(), name='tenant-join'),
    *router.urls,
]
