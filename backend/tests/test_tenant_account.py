import pytest
from rest_framework.test import APIClient

from records.models import TenancyMessage
from tenancies.models import Tenant
from tests.test_rules import make_tenancy, signup


pytestmark = pytest.mark.django_db


def test_a_tenant_creates_their_own_account_from_the_link():
    landlord = APIClient()
    signup(landlord)
    tenancy = make_tenancy(landlord)

    created = landlord.post(f"/api/tenancies/{tenancy['id']}/tenants/", {
        'name': 'Sam Cousin',
        'email': 'sam@example.com',
        'phone': '780-555-0144',
    }, format='json')
    assert created.status_code == 201, created.data
    assert created.data['has_account'] is False
    assert created.data['account_path'].startswith('/join/')
    assert Tenant.objects.filter(tenancy_id=tenancy['id'], email='sam@example.com').count() == 1

    blocked = APIClient()
    assert blocked.post('/api/auth/login/', {
        'email': 'sam@example.com',
        'password': 'correct-horse-9',
    }, format='json').status_code == 400

    token = created.data['account_path'].removeprefix('/join/')
    preview = APIClient().get(f'/api/join/{token}/')
    assert preview.status_code == 200
    assert preview.data['email'] == 'sam@example.com'
    assert preview.data['has_account'] is False

    weak = APIClient().post(f'/api/join/{token}/', {'password': 'short'}, format='json')
    assert weak.status_code == 400

    tenant = APIClient()
    claimed = tenant.post(f'/api/join/{token}/', {'password': 'correct-horse-9'}, format='json')
    assert claimed.status_code == 201, claimed.data
    assert claimed.data['role'] == 'tenant'
    assert tenant.get('/api/properties/').status_code == 403
    assert tenant.get('/api/home/').status_code == 403

    home = tenant.get('/api/tenant/home/')
    assert home.status_code == 200, home.data
    assert home.data['unit'] == 'Basement suite'
    assert any(row['kind'] == 'rent_due' for row in home.data['reminders'])

    note = tenant.post('/api/tenant/messages/', {'body': 'The heat is uneven in the main room.'}, format='json')
    assert note.status_code == 201, note.data
    assert TenancyMessage.objects.filter(tenancy_id=tenancy['id'], author_role='tenant').count() == 1
    assert APIClient().get(f'/api/join/{token}/').status_code == 404

    again = landlord.post(f"/api/tenancies/{tenancy['id']}/tenants/", {
        'name': 'Sam Cousin',
        'email': 'sam@example.com',
    }, format='json')
    assert again.status_code == 400


def test_several_tenants_each_get_their_own_account_link():
    landlord = APIClient()
    signup(landlord)
    tenancy = make_tenancy(landlord)
    created = landlord.post(f"/api/tenancies/{tenancy['id']}/tenants/", {
        'tenants': [
            {'name': 'Alex Cousin', 'email': 'alex@example.com', 'phone': ''},
            {'name': 'Riley Cousin', 'email': 'riley@example.com', 'phone': '780-555-0102'},
        ],
    }, format='json')
    assert created.status_code == 201, created.data
    paths = {row['email']: row['account_path'] for row in created.data['tenants']}
    assert paths['alex@example.com'] != paths['riley@example.com']
    assert all(row['has_account'] is False for row in created.data['tenants'])

    properties = landlord.get('/api/properties/')
    names = {person['name'] for person in properties.data[0]['units'][0]['tenants']}
    assert names == {'Sam Cousin', 'Alex Cousin', 'Riley Cousin'}

    duplicate = landlord.post(f"/api/tenancies/{tenancy['id']}/tenants/", {
        'tenants': [
            {'name': 'One', 'email': 'one@example.com'},
            {'name': 'Also One', 'email': 'one@example.com'},
        ],
    }, format='json')
    assert duplicate.status_code == 400
    assert Tenant.objects.filter(email='one@example.com').count() == 0
