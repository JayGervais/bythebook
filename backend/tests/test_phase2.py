from datetime import date

import pytest
from rest_framework.test import APIClient

from records.services import prepare_notice
from records.timelines import earliest_monthly_end, earliest_rent_increase, earliest_weekly_end
from tenancies.models import Tenancy
from tests.test_rules import make_tenancy, signup


pytestmark = pytest.mark.django_db


def test_register_returns_a_token_for_the_phone_app():
    api = APIClient()
    created = api.post('/api/auth/register/', {
        'email': 'mobile@example.com',
        'password': 'correct-horse-9',
        'full_name': 'Mobile Landlord',
    }, format='json')
    assert created.status_code == 201, created.data
    token = created.data['token']
    phone = APIClient()
    phone.credentials(HTTP_AUTHORIZATION=f'Token {token}')
    me = phone.get('/api/auth/me/')
    assert me.status_code == 200
    assert me.data['email'] == 'mobile@example.com'
    assert phone.post('/api/auth/logout/').status_code == 204
    assert phone.get('/api/auth/me/').status_code in (401, 403)


def test_monthly_landlord_notice_uses_three_tenancy_months():
    assert earliest_monthly_end(date(2026, 6, 1), 1, 3) == date(2026, 8, 31)
    assert earliest_monthly_end(date(2026, 6, 2), 1, 3) == date(2026, 9, 30)


def test_weekly_notice_ends_on_the_tenancy_week():
    # 1 June 2026 is a Monday, matching a tenancy that started on Monday.
    assert date(2026, 6, 1).weekday() == 0
    assert earliest_weekly_end(date(2026, 6, 1), 0) == date(2026, 6, 7)
    assert earliest_weekly_end(date(2026, 6, 2), 0) == date(2026, 6, 14)


def test_rent_increase_waits_for_notice_and_a_year():
    assert earliest_rent_increase(date(2026, 6, 1), 'monthly', 1, 0) == date(2026, 9, 1)
    api = APIClient()
    signup(api)
    tenancy = Tenancy.objects.get(pk=make_tenancy(api)['id'])
    _fields, errors = prepare_notice(tenancy, {
        'kind': 'rent_increase',
        'served_on': date(2026, 11, 5),
        'effective_on': date(2027, 2, 1),
        'service_method': 'personal',
        'new_rent': '1500.00',
    })
    assert 'effective_on' in errors
    fields, errors = prepare_notice(tenancy, {
        'kind': 'rent_increase',
        'served_on': date(2026, 11, 5),
        'effective_on': date(2027, 11, 5),
        'service_method': 'personal',
        'new_rent': '1500.00',
    })
    assert errors == {}
    assert 'increase to $1500.00' in fields['body']


def test_fixed_term_blocks_a_rent_increase_and_a_periodic_notice():
    api = APIClient()
    signup(api)
    created = make_tenancy(api, period='fixed', end_date='2027-11-05')
    tenancy = Tenancy.objects.get(pk=created['id'])
    _fields, errors = prepare_notice(tenancy, {
        'kind': 'rent_increase',
        'served_on': date(2027, 1, 1),
        'effective_on': date(2028, 1, 1),
        'service_method': 'personal',
        'new_rent': '1600.00',
    })
    assert 'fixed term' in errors['kind']
    _fields, errors = prepare_notice(tenancy, {
        'kind': 'terminate_periodic',
        'served_on': date(2027, 1, 1),
        'effective_on': date(2027, 4, 30),
        'service_method': 'personal',
        'reason_code': 'landlord_occupy',
    })
    assert 'fixed term' in errors['kind']


def test_entry_notice_rejects_sunday_and_short_notice():
    api = APIClient()
    signup(api)
    tenancy = Tenancy.objects.get(pk=make_tenancy(api)['id'])
    _fields, errors = prepare_notice(tenancy, {
        'kind': 'entry',
        'served_on': date(2026, 11, 6),
        'served_time': '09:00',
        'effective_on': date(2026, 11, 8),
        'effective_time': '10:00',
        'service_method': 'personal',
        'reason': 'Inspect the furnace.',
    })
    assert 'Sunday' in errors['effective_on']
    _fields, errors = prepare_notice(tenancy, {
        'kind': 'entry',
        'served_on': date(2026, 11, 9),
        'served_time': '09:00',
        'effective_on': date(2026, 11, 9),
        'effective_time': '12:00',
        'service_method': 'personal',
        'reason': 'Inspect the furnace.',
    })
    assert '24 hours' in errors['effective_on']


def test_rent_log_notice_and_packet():
    api = APIClient()
    signup(api)
    tenancy = make_tenancy(api)
    payment = api.post(f"/api/tenancies/{tenancy['id']}/payments/", {
        'amount': '1400.00',
        'paid_on': '2026-11-05',
        'method': 'etransfer',
        'note': 'November',
    }, format='json')
    assert payment.status_code == 201, payment.data
    assert payment.data['receipt_number'] == '0001'
    second = api.post(f"/api/tenancies/{tenancy['id']}/payments/", {
        'amount': '1400.00',
        'paid_on': '2026-12-01',
        'method': 'etransfer',
    }, format='json')
    assert second.data['receipt_number'] == '0002'
    receipt = api.get(f"/api/tenancies/{tenancy['id']}/payments/{payment.data['id']}/receipt.pdf")
    assert receipt.status_code == 200
    assert receipt.content.startswith(b'%PDF')

    notice = api.post(f"/api/tenancies/{tenancy['id']}/notices/", {
        'kind': 'substantial_breach',
        'served_on': '2026-11-05',
        'effective_on': '2026-11-19',
        'service_method': 'personal',
        'reason_code': 'nonpayment',
        'reason': 'November rent of $1,400 was not paid.',
    }, format='json')
    assert notice.status_code == 201, notice.data
    assert 'will not end if' in notice.data['body']
    too_soon = api.post(f"/api/tenancies/{tenancy['id']}/notices/", {
        'kind': 'substantial_breach',
        'served_on': '2026-11-05',
        'effective_on': '2026-11-18',
        'service_method': 'personal',
        'reason_code': 'nonpayment',
        'reason': 'November rent was not paid.',
    }, format='json')
    assert too_soon.status_code == 400

    message = api.post(f"/api/tenancies/{tenancy['id']}/messages/", {'body': 'Rent was short.'}, format='json')
    assert message.status_code == 201
    packet = api.get(f"/api/tenancies/{tenancy['id']}/packet.pdf")
    assert packet.status_code == 200
    assert packet.content.startswith(b'%PDF')


def test_tenant_can_log_a_maintenance_request(settings):
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    api = APIClient()
    signup(api)
    tenancy = make_tenancy(api)
    tenant_id = tenancy['tenants'][0]['id']
    invite = api.post(f'/api/tenants/{tenant_id}/invite/')
    assert invite.status_code == 200, invite.data
    token = invite.data['path'].rsplit('/', 1)[-1]
    guest = APIClient()
    created = guest.post(f'/api/invite/{token}/requests/', {'description': 'The heat is not coming on.'}, format='json')
    assert created.status_code == 201, created.data
    assert created.data['requested_by'] == 'tenant'
    note = guest.post(f'/api/invite/{token}/messages/', {'body': 'It started last night.'}, format='json')
    assert note.status_code == 201
    tasks = api.get('/api/properties/').data[0]['units'][0]['tasks']
    assert {task['kind'] for task in tasks} == {'furnace', 'smoke_co', 'filter'}
    done = api.post(f"/api/maintenance-tasks/{tasks[0]['id']}/done/", {'done_on': '2026-11-05'}, format='json')
    assert done.status_code == 200, done.data
    assert done.data['last_done_on'] == '2026-11-05'
