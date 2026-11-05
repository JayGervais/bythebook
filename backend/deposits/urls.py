from django.urls import path

from deposits.views import DeductionView, DepositStatementPdfView, DepositView, InterestView

urlpatterns = [
    path('tenancies/<uuid:tenancy_id>/deposit/', DepositView.as_view(), name='deposit'),
    path('tenancies/<uuid:tenancy_id>/deposit/interest/', InterestView.as_view(), name='deposit-interest'),
    path('tenancies/<uuid:tenancy_id>/deposit/deductions/', DeductionView.as_view(), name='deposit-deduction'),
    path('tenancies/<uuid:tenancy_id>/deposit/statement.pdf', DepositStatementPdfView.as_view(), name='deposit-statement'),
]
