from calendar import monthrange
from datetime import date, timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.contrib.auth import login
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsLandlord
from deposits.models import Reminder
from records.models import MaintenanceTask, TenancyMessage
from records.serializers import MaintenanceTaskSerializer, MessageSerializer
from records.services import ensure_schedule
from tenancies.accounts import TenantAccountError, add_tenant, claim_tenant_account, issue_account_link, tenant_from_account_token
from tenancies.invites import issue_invite
from tenancies.models import Tenancy, Tenant
from tenancies.serializers import TenancyExportSerializer, TenancySerializer, TenantSerializer

TENANT_REMINDER_KINDS = (
    Reminder.Kind.INSPECTION_MOVE_IN,
    Reminder.Kind.INSPECTION_MOVE_OUT,
    Reminder.Kind.NOTICE_OF_LANDLORD,
    Reminder.Kind.LEASE_COPY,
    Reminder.Kind.DEPOSIT_STATEMENT,
)


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
    permission_classes = [IsLandlord]

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
    permission_classes = [IsLandlord]

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


class TenantAccountView(APIView):
    permission_classes = [IsLandlord]

    def post(self, request, tenancy_id):
        tenancy = get_object_or_404(owned_tenancies(request.user), pk=tenancy_id)
        if tenancy.status == Tenancy.Status.ENDED:
            return Response(
                {'detail': 'This tenancy has ended. Start a new one before adding a tenant.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        rows = request.data.get('tenants')
        single = not isinstance(rows, list)
        if single:
            rows = [request.data]
        if not rows:
            return Response({'detail': 'Add at least one tenant.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            created = _open_many(tenancy, rows, request.user)
        except TenantAccountError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        payload = [_with_account_link(tenant, raw, emailed) for tenant, raw, emailed in created]
        if single:
            return Response(payload[0], status=status.HTTP_201_CREATED)
        return Response({'tenants': payload}, status=status.HTTP_201_CREATED)


def _open_many(tenancy, rows, landlord):
    created = []
    seen = set()
    with transaction.atomic():
        for row in rows:
            if not isinstance(row, dict):
                raise TenantAccountError('Each tenant needs a name and email.')
            email = str(row.get('email') or '').strip().lower()
            if email and email in seen:
                raise TenantAccountError('Each tenant needs a different email.')
            if email:
                seen.add(email)
            tenant, raw = add_tenant(
                tenancy,
                name=str(row.get('name') or ''),
                email=email,
                phone=str(row.get('phone') or ''),
            )
            emailed = _email_account_link(tenant, raw, landlord)
            created.append((tenant, raw, emailed))
    return created


def _account_path(raw: str) -> str:
    return f'/join/{raw}'


def _with_account_link(tenant, raw: str, emailed: bool):
    payload = TenantSerializer(tenant).data
    payload['account_path'] = _account_path(raw)
    payload['emailed'] = emailed
    return payload


def _email_account_link(tenant, raw: str, landlord) -> bool:
    if not tenant.email:
        return False
    prop = tenant.tenancy.unit.property
    link = f'{settings.FRONTEND_ORIGIN}{_account_path(raw)}'
    sender = landlord.full_name or 'Your landlord'
    send_mail(
        subject='Create your rental account',
        message=(
            f'{sender} added you to {prop.street_address}, {prop.city}.\n\n'
            'Create your account to see reminders and send messages. You choose the password.\n\n'
            f'{link}\n\n'
            'This link expires in 14 days.\n\n'
            f'{settings.NOT_LEGAL_ADVICE}'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[tenant.email],
        fail_silently=True,
    )
    return True


class TenantAccountLinkView(APIView):
    permission_classes = [IsLandlord]

    def post(self, request, tenant_id):
        tenant = get_object_or_404(
            Tenant.objects.filter(tenancy__unit__property__landlord=request.user),
            pk=tenant_id,
        )
        if tenant.account_id:
            return Response({'detail': 'This tenant already has an account.'}, status=status.HTTP_400_BAD_REQUEST)
        if not tenant.email:
            return Response({'detail': 'Add an email before sending an account link.'}, status=status.HTTP_400_BAD_REQUEST)
        raw = issue_account_link(tenant)
        emailed = _email_account_link(tenant, raw, request.user)
        return Response({'name': tenant.name, 'email': tenant.email, 'path': _account_path(raw), 'emailed': emailed})


class TenantJoinView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        tenant = tenant_from_account_token(token)
        if tenant is None:
            return Response({'detail': 'This link is invalid or has expired.'}, status=status.HTTP_404_NOT_FOUND)
        prop = tenant.tenancy.unit.property
        return Response({
            'name': tenant.name,
            'email': tenant.email,
            'address': f'{prop.street_address}, {prop.city}',
            'unit': tenant.tenancy.unit.label,
            'has_account': bool(tenant.account_id),
        })

    def post(self, request, token):
        tenant = tenant_from_account_token(token)
        if tenant is None:
            return Response({'detail': 'This link is invalid or has expired.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            user = claim_tenant_account(tenant, str(request.data.get('password') or ''))
        except TenantAccountError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        login(request, user)
        from accounts.views import _with_token
        return Response(_with_token(user), status=status.HTTP_201_CREATED)


def _tenant_for_user(user):
    if getattr(user, 'role', '') != 'tenant':
        return None
    return (
        Tenant.objects.filter(account=user)
        .select_related('tenancy', 'tenancy__unit', 'tenancy__unit__property')
        .first()
    )


def _next_rent_due(tenancy, today: date) -> date:
    year, month = today.year, today.month
    day = min(tenancy.rent_due_day, monthrange(year, month)[1])
    due = date(year, month, day)
    if due < today:
        if month == 12:
            year, month = year + 1, 1
        else:
            month += 1
        day = min(tenancy.rent_due_day, monthrange(year, month)[1])
        due = date(year, month, day)
    return due


class TenantHomeView(APIView):
    def get(self, request):
        tenant = _tenant_for_user(request.user)
        if tenant is None:
            return Response({'detail': 'This account is not a tenant.'}, status=status.HTTP_403_FORBIDDEN)
        tenancy = tenant.tenancy
        today = timezone.localdate()
        reminders = []
        if tenancy.status != Tenancy.Status.ENDED:
            due = _next_rent_due(tenancy, today)
            reminders.append({
                'id': 'rent',
                'kind': 'rent_due',
                'due_on': due,
                'headline': 'Pay the rent',
                'detail': f'Rent of ${tenancy.rent_amount} is due on day {tenancy.rent_due_day} of each month.',
                'unit': tenancy.unit.label,
            })
        for reminder in tenancy.reminders.filter(completed_at__isnull=True, kind__in=TENANT_REMINDER_KINDS).order_by('due_on'):
            reminders.append({
                'id': str(reminder.id),
                'kind': reminder.kind,
                'due_on': reminder.due_on,
                'headline': reminder.headline,
                'detail': reminder.detail,
                'unit': tenancy.unit.label,
            })
        prop = tenancy.unit.property
        return Response({
            'name': tenant.name,
            'address': f'{prop.street_address}, {prop.city}',
            'unit': tenancy.unit.label,
            'rent_amount': str(tenancy.rent_amount),
            'messages': MessageSerializer(tenancy.messages.all(), many=True).data,
            'reminders': reminders,
        })


class TenantMessageView(APIView):
    def post(self, request):
        tenant = _tenant_for_user(request.user)
        if tenant is None:
            return Response({'detail': 'This account is not a tenant.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = MessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = TenancyMessage.objects.create(
            tenancy=tenant.tenancy,
            author_role=TenancyMessage.Role.TENANT,
            author_name=tenant.name or request.user.full_name or request.user.email,
            body=serializer.validated_data['body'],
        )
        return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)
