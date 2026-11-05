from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from deposits.services import sync_reminders
from inspections.delivery import finish_inspection
from inspections.models import Inspection, InspectionItem, Photo, Signature
from inspections.pdf import render_inspection_pdf
from inspections.serializers import InspectionSerializer, PublicInspectionSerializer
from inspections.services import ROLES_FOR_PRESENCE, client_ip, revise_inspection
from tenancies.invites import tenant_from_token
from tenancies.models import Tenancy


def _owned_inspections(user):
    return Inspection.objects.filter(tenancy__unit__property__landlord=user).select_related(
        'tenancy', 'tenancy__unit', 'tenancy__unit__property',
    )


def _inspection_response(inspection, warning=''):
    inspection = _owned_inspections(inspection.tenancy.unit.property.landlord).prefetch_related(
        'items__photos', 'signatures',
    ).get(pk=inspection.pk)
    payload = InspectionSerializer(inspection).data
    if warning:
        payload['warning'] = warning
    return payload


class InspectionDetailView(APIView):
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_object(self, request, inspection_id):
        return get_object_or_404(_owned_inspections(request.user), pk=inspection_id)

    def get(self, request, inspection_id):
        inspection = self.get_object(request, inspection_id)
        return Response(_inspection_response(inspection))

    def patch(self, request, inspection_id):
        inspection = self.get_object(request, inspection_id)
        serializer = InspectionSerializer(inspection, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(_inspection_response(serializer.instance))


class InspectionPdfView(APIView):
    def get(self, request, inspection_id):
        inspection = get_object_or_404(_owned_inspections(request.user), pk=inspection_id)
        pdf = render_inspection_pdf(inspection)
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{inspection.inspection_type}-v{inspection.version}.pdf"'
        return response


class InspectionFinalizeView(APIView):
    def post(self, request, inspection_id):
        inspection = get_object_or_404(_owned_inspections(request.user), pk=inspection_id)
        blockers, warning = finish_inspection(inspection)
        payload = _inspection_response(inspection, warning)
        payload['blockers'] = blockers
        if blockers:
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
        return Response(payload)


class InspectionReviseView(APIView):
    def post(self, request, inspection_id):
        inspection = get_object_or_404(_owned_inspections(request.user), pk=inspection_id)
        try:
            revision = revise_inspection(inspection)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        sync_reminders(revision.tenancy)
        return Response(_inspection_response(revision), status=status.HTTP_201_CREATED)


class InspectionCopyHandedView(APIView):
    def post(self, request, inspection_id):
        inspection = get_object_or_404(_owned_inspections(request.user), pk=inspection_id)
        if not inspection.is_locked:
            return Response(
                {'detail': 'Finish the report before you mark the copy as handed over.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        inspection.copy_sent_at = inspection.copy_sent_at or timezone.now()
        inspection.copy_warning = ''
        inspection.save(update_fields=['copy_sent_at', 'copy_warning'])
        sync_reminders(inspection.tenancy)
        return Response(_inspection_response(inspection))


class InspectionPhotoView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, inspection_id, item_id):
        inspection = get_object_or_404(_owned_inspections(request.user), pk=inspection_id)
        if inspection.is_locked:
            return Response({'detail': 'This report is finished.'}, status=status.HTTP_400_BAD_REQUEST)
        item = get_object_or_404(InspectionItem, pk=item_id, inspection=inspection)
        upload = request.FILES.get('image')
        if upload is None:
            return Response({'detail': 'Choose a photo first.'}, status=status.HTTP_400_BAD_REQUEST)
        photo = Photo.objects.create(
            item=item,
            image=upload,
            caption=str(request.data.get('caption', ''))[:200],
        )
        return Response({'id': str(photo.id), 'url': photo.image.url, 'caption': photo.caption}, status=status.HTTP_201_CREATED)


class PhotoDeleteView(APIView):
    def delete(self, request, photo_id):
        photo = get_object_or_404(
            Photo.objects.filter(item__inspection__tenancy__unit__property__landlord=request.user),
            pk=photo_id,
        )
        if photo.item.inspection.is_locked:
            return Response({'detail': 'This report is finished.'}, status=status.HTTP_400_BAD_REQUEST)
        photo.image.delete(save=False)
        photo.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def _store_signature(inspection, role, name, upload, request):
    if inspection.is_locked:
        return 'This report is finished.'
    if role not in ROLES_FOR_PRESENCE[inspection.presence]:
        return 'That signature does not belong on this kind of report.'
    if upload is None:
        return 'Draw a signature first.'
    if not name.strip():
        return 'Add the name of the person signing.'
    if role == Signature.Role.TENANT_AGREE:
        inspection.signatures.filter(role=Signature.Role.TENANT_DISAGREE).delete()
    if role == Signature.Role.TENANT_DISAGREE:
        inspection.signatures.filter(role=Signature.Role.TENANT_AGREE).delete()
    try:
        signature = inspection.signatures.get(role=role)
    except Signature.DoesNotExist:
        signature = Signature(inspection=inspection, role=role)
    if signature.image:
        signature.image.delete(save=False)
    signature.name = name.strip() or 'Unsigned'
    signature.image = upload
    signature.signed_at = timezone.now()
    signature.ip_address = client_ip(request)
    signature.user_agent = request.META.get('HTTP_USER_AGENT', '')[:300]
    signature.save()
    return ''


class InspectionSignatureView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, inspection_id):
        inspection = get_object_or_404(_owned_inspections(request.user), pk=inspection_id)
        role = str(request.data.get('role', '')).strip()
        if role not in Signature.Role.values:
            return Response({'detail': 'Choose which statement this signature belongs to.'}, status=status.HTTP_400_BAD_REQUEST)
        error = _store_signature(
            inspection, role, str(request.data.get('name', '')), request.FILES.get('image'), request,
        )
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        blockers, warning = ([], '')
        if request.data.get('finish') in (True, 'true', '1'):
            blockers, warning = finish_inspection(inspection)
        payload = _inspection_response(inspection, warning)
        payload['blockers'] = blockers
        status_code = status.HTTP_400_BAD_REQUEST if blockers and request.data.get('finish') in (True, 'true', '1') else status.HTTP_200_OK
        return Response(payload, status=status_code)


class InviteInspectionView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'invite'
    authentication_classes = []

    def get(self, request, token):
        tenant = tenant_from_token(token)
        if tenant is None:
            return Response({'detail': 'This link has expired. Ask for a new one.'}, status=status.HTTP_404_NOT_FOUND)
        tenancy = tenant.tenancy
        inspections = tenancy.inspections.prefetch_related('items__photos', 'signatures').order_by('inspection_type', '-version')
        prop = tenancy.unit.property
        from records.serializers import MaintenanceRequestSerializer, MessageSerializer
        return Response({
            'tenant_name': tenant.name,
            'address': f'{prop.street_address}, {prop.city}',
            'unit': tenancy.unit.label,
            'inspections': PublicInspectionSerializer(inspections, many=True).data,
            'messages': MessageSerializer(tenancy.messages.all(), many=True).data,
            'requests': MaintenanceRequestSerializer(
                tenancy.maintenance_requests.prefetch_related('photos'), many=True,
            ).data,
        })


class InviteSignView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'invite'
    authentication_classes = []
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, token):
        tenant = tenant_from_token(token)
        if tenant is None:
            return Response({'detail': 'This link has expired. Ask for a new one.'}, status=status.HTTP_404_NOT_FOUND)
        inspection = get_object_or_404(Inspection, pk=request.data.get('inspection_id'), tenancy=tenant.tenancy)
        if inspection.presence != Inspection.Presence.TOGETHER:
            return Response(
                {'detail': 'This report was not set up for a tenant signature. Talk to the landlord.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        choice = str(request.data.get('choice', '')).strip()
        if choice not in ('agree', 'disagree'):
            return Response({'detail': 'Choose agree or disagree.'}, status=status.HTTP_400_BAD_REQUEST)
        reasons = str(request.data.get('reasons', '')).strip()
        if choice == 'disagree' and not reasons:
            return Response({'detail': 'Write a short note about what you disagree with.'}, status=status.HTTP_400_BAD_REQUEST)
        if inspection.is_locked:
            return Response({'detail': 'This report is already finished.'}, status=status.HTTP_400_BAD_REQUEST)
        inspection.tenant_signer_name = str(request.data.get('name', '')).strip() or tenant.name
        inspection.disagreement_reasons = reasons if choice == 'disagree' else ''
        inspection.save(update_fields=['tenant_signer_name', 'disagreement_reasons'])
        role = Signature.Role.TENANT_AGREE if choice == 'agree' else Signature.Role.TENANT_DISAGREE
        error = _store_signature(inspection, role, inspection.tenant_signer_name, request.FILES.get('image'), request)
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        _blockers, warning = finish_inspection(inspection)
        inspection.refresh_from_db()
        return Response({
            'inspection': PublicInspectionSerializer(inspection).data,
            'warning': warning,
            'finalized': inspection.is_locked,
        })


class InvitePdfView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'invite'
    authentication_classes = []

    def get(self, request, token, inspection_id):
        tenant = tenant_from_token(token)
        if tenant is None:
            return Response({'detail': 'This link has expired. Ask for a new one.'}, status=status.HTTP_404_NOT_FOUND)
        inspection = get_object_or_404(Inspection, pk=inspection_id, tenancy=tenant.tenancy)
        pdf = render_inspection_pdf(inspection)
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="inspection-report.pdf"'
        return response


class TenancyInspectionCreateView(APIView):
    def post(self, request, tenancy_id):
        tenancy = get_object_or_404(
            Tenancy.objects.filter(unit__property__landlord=request.user),
            pk=tenancy_id,
        )
        inspection_type = request.data.get('inspection_type', Inspection.Type.MOVE_IN)
        if inspection_type not in Inspection.Type.values:
            return Response({'detail': 'Choose move-in or move-out.'}, status=status.HTTP_400_BAD_REQUEST)
        from inspections.services import create_inspection
        inspection = create_inspection(tenancy, inspection_type)
        sync_reminders(tenancy)
        return Response(_inspection_response(inspection), status=status.HTTP_201_CREATED)
