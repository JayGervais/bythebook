from datetime import date, timedelta

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from records.models import MaintenancePhoto, MaintenanceRequest, MaintenanceTask, Notice, RentPayment, TenancyMessage
from records.notices import catalog
from records.pdf import render_notice_pdf, render_packet, render_receipt
from records.serializers import (
    MaintenanceRequestSerializer,
    MaintenanceTaskSerializer,
    MessageSerializer,
    NoticeSerializer,
    RentPaymentSerializer,
)
from records.services import complete_task, record_payment
from tenancies.invites import tenant_from_token
from tenancies.views import owned_tenancies


class NoticeCatalogView(APIView):
    def get(self, request):
        return Response(catalog())


class RentPaymentListView(APIView):
    def post(self, request, tenancy_id):
        tenancy = get_object_or_404(owned_tenancies(request.user), pk=tenancy_id)
        serializer = RentPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        payment = record_payment(tenancy, data['amount'], data['paid_on'], data.get('method') or 'etransfer', data.get('note') or '')
        return Response(RentPaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


class RentReceiptView(APIView):
    def get(self, request, tenancy_id, payment_id):
        payment = get_object_or_404(
            RentPayment.objects.filter(tenancy__unit__property__landlord=request.user, tenancy_id=tenancy_id),
            pk=payment_id,
        )
        pdf = render_receipt(payment)
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="receipt-{payment.receipt_number}.pdf"'
        return response


class NoticeListView(APIView):
    def post(self, request, tenancy_id):
        tenancy = get_object_or_404(owned_tenancies(request.user), pk=tenancy_id)
        serializer = NoticeSerializer(data=request.data, context={'tenancy': tenancy})
        serializer.is_valid(raise_exception=True)
        notice = serializer.save()
        return Response(NoticeSerializer(notice).data, status=status.HTTP_201_CREATED)


class NoticePdfView(APIView):
    def get(self, request, tenancy_id, notice_id):
        notice = get_object_or_404(
            Notice.objects.filter(tenancy__unit__property__landlord=request.user, tenancy_id=tenancy_id),
            pk=notice_id,
        )
        pdf = render_notice_pdf(notice)
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="notice-{notice.kind}.pdf"'
        return response


class ApplyRentIncreaseView(APIView):
    def post(self, request, tenancy_id, notice_id):
        notice = get_object_or_404(
            Notice.objects.filter(tenancy__unit__property__landlord=request.user, tenancy_id=tenancy_id, kind=Notice.Kind.RENT),
            pk=notice_id,
        )
        if timezone.localdate() < notice.effective_on:
            return Response(
                {'detail': f'This increase takes effect on {notice.effective_on.isoformat()}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        notice.tenancy.rent_amount = notice.new_rent
        notice.tenancy.save(update_fields=['rent_amount', 'status'])
        return Response({'rent_amount': str(notice.tenancy.rent_amount)})


class MessageListView(APIView):
    def post(self, request, tenancy_id):
        tenancy = get_object_or_404(owned_tenancies(request.user), pk=tenancy_id)
        serializer = MessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = TenancyMessage.objects.create(
            tenancy=tenancy,
            author_role=TenancyMessage.Role.LANDLORD,
            author_name=request.user.full_name or request.user.email,
            body=serializer.validated_data['body'],
        )
        return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)


class PacketView(APIView):
    def get(self, request, tenancy_id):
        tenancy = get_object_or_404(owned_tenancies(request.user), pk=tenancy_id)
        pdf = render_packet(tenancy)
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="tenancy-{tenancy.id}.pdf"'
        return response


class MaintenanceRequestListView(APIView):
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def post(self, request, unit_id):
        from properties.models import Unit
        unit = get_object_or_404(Unit.objects.filter(property__landlord=request.user), pk=unit_id)
        description = str(request.data.get('description') or '').strip()
        if not description:
            return Response({'description': 'Describe what needs attention.'}, status=status.HTTP_400_BAD_REQUEST)
        tenancy_id = request.data.get('tenancy') or None
        tenancy = None
        if tenancy_id:
            tenancy = get_object_or_404(owned_tenancies(request.user), pk=tenancy_id, unit=unit)
        record = MaintenanceRequest.objects.create(
            unit=unit,
            tenancy=tenancy,
            description=description,
            requested_by=MaintenanceRequest.Requester.LANDLORD,
            requester_name=request.user.full_name or request.user.email,
        )
        _save_photo(record, request.FILES.get('image'))
        return Response(MaintenanceRequestSerializer(record).data, status=status.HTTP_201_CREATED)


class MaintenanceRequestDetailView(APIView):
    def patch(self, request, request_id):
        record = get_object_or_404(
            MaintenanceRequest.objects.filter(unit__property__landlord=request.user),
            pk=request_id,
        )
        status_value = request.data.get('status', record.status)
        if status_value not in MaintenanceRequest.Status.values:
            return Response({'status': 'Choose open, in progress, or resolved.'}, status=status.HTTP_400_BAD_REQUEST)
        record.status = status_value
        if status_value == MaintenanceRequest.Status.RESOLVED:
            record.resolved_on = timezone.localdate()
        elif status_value != MaintenanceRequest.Status.RESOLVED:
            record.resolved_on = None
        record.save(update_fields=['status', 'resolved_on'])
        return Response(MaintenanceRequestSerializer(record).data)


class MaintenanceTaskDoneView(APIView):
    def post(self, request, task_id):
        task = get_object_or_404(
            MaintenanceTask.objects.filter(unit__property__landlord=request.user),
            pk=task_id,
        )
        raw = str(request.data.get('done_on') or timezone.localdate().isoformat())
        try:
            done_on = date.fromisoformat(raw[:10])
        except ValueError:
            return Response({'done_on': 'Use a real date.'}, status=status.HTTP_400_BAD_REQUEST)
        if done_on > timezone.localdate() + timedelta(days=1):
            return Response({'done_on': 'The completion date cannot be in the future.'}, status=status.HTTP_400_BAD_REQUEST)
        complete_task(task, done_on)
        return Response(MaintenanceTaskSerializer(task).data)


class InviteMessageView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'invite'

    def post(self, request, token):
        tenant = tenant_from_token(token)
        if tenant is None:
            return Response({'detail': 'This link has expired. Ask for a new one.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = MessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = TenancyMessage.objects.create(
            tenancy=tenant.tenancy,
            author_role=TenancyMessage.Role.TENANT,
            author_name=tenant.name,
            body=serializer.validated_data['body'],
        )
        return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)


class InviteMaintenanceView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'invite'
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, token):
        tenant = tenant_from_token(token)
        if tenant is None:
            return Response({'detail': 'This link has expired. Ask for a new one.'}, status=status.HTTP_404_NOT_FOUND)
        description = str(request.data.get('description') or '').strip()
        if not description:
            return Response({'description': 'Describe what needs attention.'}, status=status.HTTP_400_BAD_REQUEST)
        record = MaintenanceRequest.objects.create(
            unit=tenant.tenancy.unit,
            tenancy=tenant.tenancy,
            description=description,
            requested_by=MaintenanceRequest.Requester.TENANT,
            requester_name=tenant.name,
        )
        _save_photo(record, request.FILES.get('image'))
        return Response(MaintenanceRequestSerializer(record).data, status=status.HTTP_201_CREATED)


def _save_photo(record, upload):
    if not upload:
        return
    MaintenancePhoto.objects.create(request=record, image=upload, caption='')
