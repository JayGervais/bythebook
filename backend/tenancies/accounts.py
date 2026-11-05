import hashlib
import secrets
from datetime import timedelta

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone

from accounts.models import User
from tenancies.models import Tenant, Tenancy


class TenantAccountError(Exception):
    pass


def add_tenant(tenancy: Tenancy, *, name: str, email: str, phone: str) -> tuple[Tenant, str]:
    """Record a person on the tenancy and return a one-time link so they can create their account."""
    name = name.strip()
    email = email.strip().lower()
    phone = phone.strip()
    if not name:
        raise TenantAccountError('Add the tenant name.')
    if not email:
        raise TenantAccountError('Add an email so the tenant can create an account.')

    existing_user = User.objects.filter(email=email).first()
    if existing_user is not None and existing_user.role != User.Role.TENANT:
        raise TenantAccountError('That email already belongs to a landlord account.')
    if existing_user is not None:
        try:
            linked = existing_user.tenant_record
        except Tenant.DoesNotExist:
            linked = None
        if linked is not None:
            raise TenantAccountError('This person already has a tenant account.')

    tenant = tenancy.tenants.filter(email__iexact=email).first()
    if tenant is not None and tenant.account_id:
        raise TenantAccountError('This tenant already has an account.')
    if tenant is None:
        tenant = Tenant(tenancy=tenancy)
    tenant.name = name
    tenant.email = email
    tenant.phone = phone or tenant.phone
    tenant.save()
    return tenant, issue_account_link(tenant)


def issue_account_link(tenant: Tenant) -> str:
    raw = secrets.token_urlsafe(32)
    tenant.account_token_hash = hashlib.sha256(raw.encode()).hexdigest()
    tenant.account_token_expires_at = timezone.now() + timedelta(days=14)
    tenant.save(update_fields=['account_token_hash', 'account_token_expires_at'])
    return raw


def tenant_from_account_token(raw: str) -> Tenant | None:
    if not raw:
        return None
    digest = hashlib.sha256(raw.encode()).hexdigest()
    tenant = (
        Tenant.objects.filter(account_token_hash=digest)
        .select_related('tenancy', 'tenancy__unit', 'tenancy__unit__property', 'tenancy__unit__property__landlord')
        .first()
    )
    if tenant is None or tenant.account_token_expires_at is None:
        return None
    if tenant.account_token_expires_at < timezone.now():
        return None
    return tenant


def claim_tenant_account(tenant: Tenant, password: str) -> User:
    if tenant.account_id:
        raise TenantAccountError('This account is already set up. Sign in with your email.')
    try:
        validate_password(password, User(email=tenant.email, full_name=tenant.name))
    except ValidationError as exc:
        raise TenantAccountError(' '.join(exc.messages)) from exc
    if User.objects.filter(email=tenant.email).exists():
        raise TenantAccountError('That email already belongs to an account. Sign in instead.')
    user = User.objects.create_user(
        email=tenant.email,
        password=password,
        full_name=tenant.name,
        phone=tenant.phone,
        role=User.Role.TENANT,
    )
    tenant.account = user
    tenant.account_token_hash = ''
    tenant.account_token_expires_at = None
    tenant.save(update_fields=['account', 'account_token_hash', 'account_token_expires_at'])
    return user
