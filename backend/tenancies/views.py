from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from deposits.models import Reminder
from records.models import MaintenanceTask
from records.serializers import MaintenanceTaskSerializer
from records.services import ensure_schedule
from tenancies.invites import issue_invite
from tenancies.models import Tenancy, Tenant
from tenancies.serializers import TenancyExportSerializer, TenancySerializer


def owned_tenancies(user):
    return (
        Tenancy.objects.filter(unit__property__landlord=user)
        .select_related('unit', 'unit__property', 'deposit')
        .prefetch_related(
            'tenants', 'inspections', 'reminders', 'payments', 'notices', 'messages',
            'maintenance_requests__photos', 'deposit__interest_entries', 'deposit__deductions',
        )
    )


class TenancyViewSet(viewsets.ModelViewSet):
    serializer_class = TenancySerializer

    def get_queryset(self):
        return owned_tenancies(self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['tenancy'] = None
        return context


class TenancyExportView(APIView):
    def get(self, request, tenancy_id):
        tenancy = get_object_or_404(owned_tenancies(request.user), pk=tenancy_id)
        payload = TenancyExportSerializer(tenancy, context={'request': request}).data
        payload['disclaimer'] = settings.NOT_LEGAL_ADVICE
        response = JsonResponse(payload)
        response['Content-Disposition'] = f'attachment; filename="tenancy-{tenancy.id}.json"'
        return response


class TenantInviteView(APIView):
    def post(self, request, tenant_id):
        tenant = get_object_or_404(
            Tenant.objects.filter(tenancy__unit__property__landlord=request.user),
            pk=tenant_id,
        )
        raw = issue_invite(tenant)
        path = f'/invite/{raw}'
        link = f'{settings.FRONTEND_ORIGIN}{path}'
        emailed = False
        if tenant.email:
            send_mail(
                subject='A rental record to review',
                message=(
                    f'{request.user.full_name or "Your landlord"} asked you to review a record for the rental.\n\n'
                    f'{link}\n\n'
                    'This link expires in 30 days. You do not need an account.\n\n'
                    f'{settings.NOT_LEGAL_ADVICE}'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[tenant.email],
                fail_silently=True,
            )
            emailed = True
        return Response({'path': path, 'expires_at': tenant.invite_expires_at, 'emailed': emailed})


class HomeView(APIView):
    def get(self, request):
        tenancies = owned_tenancies(request.user)
        reminders = Reminder.objects.filter(
            tenancy__in=tenancies,
            completed_at__isnull=True,
        ).order_by('due_on')
        from properties.models import Unit
        for unit in Unit.objects.filter(property__landlord=request.user):
            ensure_schedule(unit)
        horizon = timezone.localdate() + timedelta(days=45)
        tasks = MaintenanceTask.objects.filter(
            unit__property__landlord=request.user,
            next_due_on__lte=horizon,
        ).select_related('unit', 'unit__property')
        return Response({
            'disclaimer': settings.NOT_LEGAL_ADVICE,
            'interest_calculator_url': settings.DEPOSIT_INTEREST_CALCULATOR_URL,
            'inspection_guide_url': settings.ALBERTA_INSPECTION_GUIDE_URL,
            'reminders': [
                {
                    'id': str(reminder.id),
                    'tenancy_id': str(reminder.tenancy_id),
                    'kind': reminder.kind,
                    'due_on': reminder.due_on,
                    'headline': reminder.headline,
                    'detail': reminder.detail,
                    'address': f'{reminder.tenancy.unit.property.street_address}',
                    'unit': reminder.tenancy.unit.label,
                }
                for reminder in reminders.select_related('tenancy__unit__property')
            ],
            'tenancies': TenancySerializer(tenancies, many=True, context={'request': request}).data,
            'maintenance': [
                {
                    **MaintenanceTaskSerializer(task).data,
                    'unit_label': task.unit.label,
                    'address': task.unit.property.street_address,
                }
                for task in tasks
            ],
        })
