from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from deposits.models import Deposit, DepositDeduction, DepositInterest
from deposits.serializers import DeductionWriteSerializer, DepositUpdateSerializer, InterestWriteSerializer
from deposits.services import sync_reminders
from inspections.pdf import render_deposit_statement
from tenancies.models import Tenancy
from tenancies.serializers import DepositSerializer


def _tenancy(user, tenancy_id):
    return get_object_or_404(
        Tenancy.objects.filter(unit__property__landlord=user),
        pk=tenancy_id,
    )


class DepositView(APIView):
    def get(self, request, tenancy_id):
        tenancy = _tenancy(request.user, tenancy_id)
        try:
            deposit = tenancy.deposit
        except Deposit.DoesNotExist:
            return Response({'deposit': None})
        return Response(DepositSerializer(deposit).data)

    def put(self, request, tenancy_id):
        tenancy = _tenancy(request.user, tenancy_id)
        serializer = DepositUpdateSerializer(data=request.data, context={'tenancy': tenancy})
        serializer.is_valid(raise_exception=True)
        try:
            deposit = tenancy.deposit
        except Deposit.DoesNotExist:
            if 'amount' not in serializer.validated_data or 'received_on' not in serializer.validated_data:
                return Response(
                    {'detail': 'Add the deposit amount and the date you received it.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            deposit = Deposit(tenancy=tenancy)
        serializer.update_deposit(deposit)
        sync_reminders(tenancy)
        return Response(DepositSerializer(deposit).data)


class InterestView(APIView):
    def post(self, request, tenancy_id):
        tenancy = _tenancy(request.user, tenancy_id)
        try:
            deposit = tenancy.deposit
        except Deposit.DoesNotExist:
            return Response({'detail': 'Record the deposit first.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = InterestWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if deposit.interest_entries.filter(covers_year=serializer.validated_data['covers_year']).exists():
            return Response(
                {'detail': 'Interest for that year is already recorded.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        DepositInterest.objects.create(deposit=deposit, **serializer.validated_data)
        sync_reminders(tenancy)
        return Response(DepositSerializer(deposit).data, status=status.HTTP_201_CREATED)


class DeductionView(APIView):
    def post(self, request, tenancy_id):
        tenancy = _tenancy(request.user, tenancy_id)
        try:
            deposit = tenancy.deposit
        except Deposit.DoesNotExist:
            return Response({'detail': 'Record the deposit first.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = DeductionWriteSerializer(data=request.data, context={'tenancy': tenancy})
        serializer.is_valid(raise_exception=True)
        DepositDeduction.objects.create(deposit=deposit, **serializer.validated_data)
        sync_reminders(tenancy)
        return Response(DepositSerializer(deposit).data, status=status.HTTP_201_CREATED)


class DepositStatementPdfView(APIView):
    def get(self, request, tenancy_id):
        tenancy = _tenancy(request.user, tenancy_id)
        try:
            deposit = tenancy.deposit
        except Deposit.DoesNotExist:
            return Response({'detail': 'There is no deposit on this tenancy.'}, status=status.HTTP_404_NOT_FOUND)
        pdf = render_deposit_statement(deposit)
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="deposit-statement.pdf"'
        return response
