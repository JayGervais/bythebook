import hashlib
import secrets
from datetime import timedelta

from django.utils import timezone

from tenancies.models import Tenant


def issue_invite(tenant: Tenant) -> str:
    raw = secrets.token_urlsafe(32)
    tenant.invite_token_hash = hashlib.sha256(raw.encode()).hexdigest()
    tenant.invite_expires_at = timezone.now() + timedelta(days=30)
    tenant.save(update_fields=['invite_token_hash', 'invite_expires_at'])
    return raw


def tenant_from_token(raw: str) -> Tenant | None:
    if not raw:
        return None
    digest = hashlib.sha256(raw.encode()).hexdigest()
    tenant = (
        Tenant.objects.filter(invite_token_hash=digest)
        .select_related('tenancy', 'tenancy__unit', 'tenancy__unit__property', 'tenancy__unit__property__landlord')
        .first()
    )
    if tenant is None or tenant.invite_expires_at is None:
        return None
    if tenant.invite_expires_at < timezone.now():
        return None
    return tenant
