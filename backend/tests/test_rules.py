from datetime import date
from io import BytesIO

import pytest
from django.core import mail
from PIL import Image
from rest_framework.test import APIClient

from accounts.models import User
from deposits.alberta_calendar import add_banking_days
from inspections.services import finalize_blockers


pytestmark = pytest.mark.django_db


def png_file(name='sign.png'):
    buffer = BytesIO()
    Image.new('RGB', (40, 16), 'black').save(buffer, format='PNG')
    buffer.seek(0)
    buffer.name = name
    return buffer


def signup(api: APIClient):
    response = api.post('/api/auth/register/', {
        'email': 'ada@example.com',
        'password': 'correct-horse-9',
        'full_name': 'Ada Landlord',
        'phone': '403-555-0100',
        'address_for_service': '12 River Ave, Calgary',
    }, format='json')
    assert response.status_code == 201, response.data
    return User.objects.get(email='ada@example.com')


def make_tenancy(api, **extra):
    prop = api.post('/api/properties/', {
        'street_address': '10 Suite Street',
        'city': 'Edmonton',
        'postal_code': 'T5J 0N3',
        'property_type': 'house_with_suite',
    }, format='json')
    assert prop.status_code == 201, prop.data
    unit = api.post('/api/units/', {
        'property': prop.data['id'],
        'label': 'Basement suite',
        'rooms_template': [{'room': 'Kitchen', 'items': ['Sink', 'Floor']}],
    }, format='json')
    assert unit.status_code == 201, unit.data
    payload = {
        'unit_id': unit.data['id'],
        'start_date': '2026-11-05',
        'rent_amount': '1400.00',
        'rent_due_day': 1,
        'tenants': [{'name': 'Sam Cousin', 'email': 'sam@example.com', 'phone': ''}],
        'deposit_amount': '1400.00',
        'deposit_received_on': '2026-11-05',
    }
    payload.update(extra)
    created = api.post('/api/tenancies/', payload, format='json')
    assert created.status_code == 201, created.data
    return created.data


def test_banking_days_skip_weekend_and_family_day():
    # Friday 13 Feb 2026, then Family Day Monday 16 Feb.
    assert add_banking_days(date(2026, 2, 13), 2) == date(2026, 2, 18)


def test_deposit_cannot_exceed_one_month_rent():
    api = APIClient()
    signup(api)
    response = api.post('/api/properties/', {
        'street_address': '10 Suite Street',
        'city': 'Edmonton',
        'property_type': 'house_with_suite',
    }, format='json')
    unit = api.post('/api/units/', {
        'property': response.data['id'],
        'label': 'Room',
    }, format='json')
    created = api.post('/api/tenancies/', {
        'unit_id': unit.data['id'],
        'start_date': '2026-11-05',
        'rent_amount': '900.00',
        'rent_due_day': 1,
        'tenants': [{'name': 'Sam', 'email': 'sam@example.com'}],
        'deposit_amount': '1800.00',
        'deposit_received_on': '2026-11-05',
    }, format='json')
    assert created.status_code == 400
    assert 'one month' in str(created.data).lower()


def test_other_provinces_are_refused():
    api = APIClient()
    signup(api)
    response = api.post('/api/properties/', {
        'street_address': '1 Main',
        'city': 'Toronto',
        'province': 'ON',
        'property_type': 'condo',
    }, format='json')
    assert response.status_code == 400


def test_finalize_requires_statements_and_signatures_then_emails_copy():
    api = APIClient()
    signup(api)
    tenancy = make_tenancy(api)
    inspection_id = tenancy['inspections'][0]['id']
    detail = api.get(f'/api/inspections/{inspection_id}/')
    assert detail.status_code == 200
    assert 'fairly represents the condition' in detail.data['statements']['agree']
    blocked = api.post(f'/api/inspections/{inspection_id}/finalize/')
    assert blocked.status_code == 400
    assert blocked.data['blockers']

    items = [{'id': item['id'], 'condition': 'good', 'notes': ''} for item in detail.data['items']]
    patched = api.patch(f'/api/inspections/{inspection_id}/', {
        'conducted_on': '2026-11-05',
        'presence': 'together',
        'landlord_name': 'Ada Landlord',
        'tenant_signer_name': 'Sam Cousin',
        'items': items,
    }, format='json')
    assert patched.status_code == 200, patched.data

    landlord_sign = api.post(
        f'/api/inspections/{inspection_id}/signatures/',
        {'role': 'landlord_presence', 'name': 'Ada Landlord', 'image': png_file()},
        format='multipart',
    )
    assert landlord_sign.status_code == 200, landlord_sign.data
    still = api.post(f'/api/inspections/{inspection_id}/finalize/')
    assert still.status_code == 400

    invite = api.post(f"/api/tenants/{tenancy['tenants'][0]['id']}/invite/")
    assert invite.status_code == 200
    token = invite.data['path'].rsplit('/', 1)[-1]
    guest = APIClient()
    signed = guest.post(
        f'/api/invite/{token}/sign/',
        {
            'inspection_id': inspection_id,
            'choice': 'agree',
            'name': 'Sam Cousin',
            'image': png_file('tenant.png'),
        },
        format='multipart',
    )
    assert signed.status_code == 200, signed.data
    assert signed.data['finalized'] is True
    assert len(mail.outbox) >= 1
    finished = api.get(f'/api/inspections/{inspection_id}/')
    assert finished.data['is_locked'] is True
    assert finished.data['copy_sent_at']
    revise = api.post(f'/api/inspections/{inspection_id}/revise/')
    assert revise.status_code == 201
    assert revise.data['version'] == 2
    assert revise.data['is_locked'] is False


def test_damage_deduction_is_blocked_until_both_reports_are_shared():
    api = APIClient()
    signup(api)
    tenancy = make_tenancy(api, end_date='2027-05-01')
    types = {row['inspection_type'] for row in tenancy['inspections']}
    assert types == {'move_in', 'move_out'}
    denied = api.post(f"/api/tenancies/{tenancy['id']}/deposit/deductions/", {
        'kind': 'damage',
        'amount': '80.00',
        'reason': 'Broken shelf',
    }, format='json')
    assert denied.status_code == 400
    assert 'move-in and move-out' in str(denied.data)
    allowed_rent = api.post(f"/api/tenancies/{tenancy['id']}/deposit/deductions/", {
        'kind': 'rent',
        'amount': '1400.00',
        'reason': 'May rent was not paid',
    }, format='json')
    assert allowed_rent.status_code == 201, allowed_rent.data


def test_move_out_keeps_move_in_condition_beside_it():
    api = APIClient()
    signup(api)
    tenancy = make_tenancy(api, end_date='2027-05-01')
    move_in = next(row for row in tenancy['inspections'] if row['inspection_type'] == 'move_in')
    detail = api.get(f"/api/inspections/{move_in['id']}/")
    items = [{'id': item['id'], 'condition': 'fair', 'notes': 'Small mark'} for item in detail.data['items']]
    api.patch(f"/api/inspections/{move_in['id']}/", {'items': items}, format='json')
    fresh = api.post(f"/api/tenancies/{tenancy['id']}/inspections/", {'inspection_type': 'move_out'}, format='json')
    assert fresh.status_code == 201
    sink = next(item for item in fresh.data['items'] if item['item'] == 'Sink')
    assert sink['prior_condition'] == 'fair'
    assert sink['prior_notes'] == 'Small mark'
    inspection = type('Obj', (), {})
    from inspections.models import Inspection
    saved = Inspection.objects.get(pk=move_in['id'])
    assert finalize_blockers(saved)


def test_trust_deadline_is_two_banking_days():
    api = APIClient()
    signup(api)
    tenancy = make_tenancy(api, deposit_received_on='2026-02-13')
    trust = next(row for row in tenancy['reminders'] if row['kind'] == 'trust_deposit')
    assert trust['due_on'] == '2026-02-18'
