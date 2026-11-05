from datetime import datetime

from django.core.files.base import ContentFile
from django.db import transaction
from deposits.alberta_calendar import ALBERTA_HOLIDAYS
from inspections.models import Inspection, InspectionItem, Signature
from inspections.statements import (
    REFUSAL_STATEMENT,
    VACANT_STATEMENT,
    absent_statement,
    agree_statement,
    disagree_statement,
    presence_statement,
)


ROLES_FOR_PRESENCE = {
    Inspection.Presence.TOGETHER: {
        Signature.Role.LANDLORD_PRESENCE,
        Signature.Role.TENANT_AGREE,
        Signature.Role.TENANT_DISAGREE,
    },
    Inspection.Presence.REFUSED: {
        Signature.Role.LANDLORD_PRESENCE,
        Signature.Role.LANDLORD_REFUSAL,
    },
    Inspection.Presence.ABSENT: {
        Signature.Role.LANDLORD_ABSENT,
    },
}


def statement_bundle(inspection: Inspection) -> dict:
    conducted = inspection.conducted_on.isoformat() if inspection.conducted_on else ''
    landlord = inspection.landlord_name.strip() or '____'
    tenant = inspection.tenant_signer_name.strip() or '____'
    bundle = {
        'vacant': VACANT_STATEMENT,
        'presence': presence_statement(conducted or '____', landlord, tenant),
        'agree': agree_statement(tenant),
        'disagree': disagree_statement(tenant),
        'refusal': REFUSAL_STATEMENT,
        'absent': absent_statement(conducted or '____', landlord),
    }
    return bundle


def _offered_time_problems(inspection: Inspection) -> list[str]:
    times = inspection.offered_times or []
    if not isinstance(times, list):
        return ['Record the two times you offered the tenant.']
    parsed = []
    for entry in times:
        if not isinstance(entry, dict):
            continue
        raw_date = str(entry.get('date') or '').strip()
        raw_time = str(entry.get('time') or '').strip()
        if not raw_date or not raw_time:
            continue
        try:
            day = datetime.strptime(raw_date, '%Y-%m-%d').date()
            clock = datetime.strptime(raw_time, '%H:%M').time()
        except ValueError:
            return ['Use a real date and a time like 18:00 for each offer.']
        parsed.append((day, clock))
    dates = {day for day, _clock in parsed}
    problems = []
    if len(dates) < 2:
        problems.append(
            'An inspection without the tenant needs two offered times, on two different days.'
        )
    for day, clock in parsed:
        if day in ALBERTA_HOLIDAYS:
            problems.append(f'{day.isoformat()} is a listed Alberta holiday. Offer a different day.')
            break
        if clock.hour < 8 or (clock.hour > 20) or (clock.hour == 20 and clock.minute > 0):
            problems.append('Offered times need to fall between 8:00 a.m. and 8:00 p.m.')
            break
    return problems


def finalize_blockers(inspection: Inspection) -> list[str]:
    blockers = []
    if not inspection.conducted_on:
        blockers.append('Add the date the inspection happened.')
    if not inspection.landlord_name.strip():
        blockers.append('Add the landlord name that should appear on the report.')
    missing_condition = inspection.items.filter(condition='').exists()
    if not inspection.items.exists():
        blockers.append('The checklist is empty.')
    elif missing_condition:
        blockers.append('Choose a condition for every item. Not applicable is fine.')

    roles = set(inspection.signatures.values_list('role', flat=True))
    if inspection.presence == Inspection.Presence.TOGETHER:
        if not inspection.tenant_signer_name.strip():
            blockers.append('Add the name of the tenant, or their agent, who walked through with you.')
        if Signature.Role.LANDLORD_PRESENCE not in roles:
            blockers.append('You still need to sign the statement about who did the inspection.')
        agreed = Signature.Role.TENANT_AGREE in roles
        disagreed = Signature.Role.TENANT_DISAGREE in roles
        if not agreed and not disagreed:
            blockers.append('The tenant still needs to sign that they agree or disagree.')
        if disagreed and not inspection.disagreement_reasons.strip():
            blockers.append('The tenant disagreed, so write their reasons on the report.')
        if agreed and disagreed:
            blockers.append('Keep one tenant signature: agree or disagree, not both.')
    elif inspection.presence == Inspection.Presence.REFUSED:
        if not inspection.tenant_signer_name.strip():
            blockers.append('Name the tenant or agent who was present and refused to sign.')
        if Signature.Role.LANDLORD_PRESENCE not in roles:
            blockers.append('Sign the statement that names who attended.')
        if Signature.Role.LANDLORD_REFUSAL not in roles:
            blockers.append('Sign the statement that the tenant refused to sign.')
    elif inspection.presence == Inspection.Presence.ABSENT:
        blockers.extend(_offered_time_problems(inspection))
        if Signature.Role.LANDLORD_ABSENT not in roles:
            blockers.append('Sign the statement that the tenant was not present.')
    return blockers


def drop_stale_signatures(inspection: Inspection):
    allowed = ROLES_FOR_PRESENCE[inspection.presence]
    inspection.signatures.exclude(role__in=allowed).delete()


def seed_items(inspection: Inspection):
    template = inspection.tenancy.unit.rooms_template or []
    prior = None
    if inspection.inspection_type == Inspection.Type.MOVE_OUT:
        prior = (
            inspection.tenancy.inspections.filter(inspection_type=Inspection.Type.MOVE_IN)
            .order_by('-version')
            .first()
        )
    prior_map = {}
    if prior is not None:
        for item in prior.items.all():
            prior_map[(item.room, item.item)] = item
    order = 0
    rows = []
    for room in template:
        name = str(room.get('room', '')).strip()
        for label in room.get('items') or []:
            label = str(label).strip()
            if not name or not label:
                continue
            previous = prior_map.get((name, label))
            rows.append(InspectionItem(
                inspection=inspection,
                room=name,
                item=label,
                sort_order=order,
                prior_condition=previous.condition if previous else '',
                prior_notes=previous.notes if previous else '',
            ))
            order += 10
    InspectionItem.objects.bulk_create(rows)


@transaction.atomic
def create_inspection(tenancy, inspection_type: str) -> Inspection:
    latest = (
        tenancy.inspections.filter(inspection_type=inspection_type).order_by('-version').first()
    )
    version = 1 if latest is None else latest.version + 1
    landlord = tenancy.unit.property.landlord
    inspection = Inspection.objects.create(
        tenancy=tenancy,
        inspection_type=inspection_type,
        version=version,
        landlord_name=landlord.full_name,
        tenant_signer_name=tenancy.tenants.order_by('name').values_list('name', flat=True).first() or '',
        scheduled_on=tenancy.start_date if inspection_type == Inspection.Type.MOVE_IN else tenancy.end_date,
    )
    seed_items(inspection)
    return inspection


def ensure_opening_inspections(tenancy):
    if not tenancy.inspections.filter(inspection_type=Inspection.Type.MOVE_IN).exists():
        create_inspection(tenancy, Inspection.Type.MOVE_IN)
    if tenancy.end_date and not tenancy.inspections.filter(inspection_type=Inspection.Type.MOVE_OUT).exists():
        create_inspection(tenancy, Inspection.Type.MOVE_OUT)


@transaction.atomic
def revise_inspection(inspection: Inspection) -> Inspection:
    if not inspection.is_locked:
        raise ValueError('Only a finished report can be revised. Edit this draft instead.')
    revision = Inspection.objects.create(
        tenancy=inspection.tenancy,
        inspection_type=inspection.inspection_type,
        version=inspection.version + 1,
        supersedes=inspection,
        scheduled_on=inspection.scheduled_on,
        conducted_on=inspection.conducted_on,
        presence=inspection.presence,
        landlord_name=inspection.landlord_name,
        tenant_signer_name=inspection.tenant_signer_name,
        disagreement_reasons=inspection.disagreement_reasons,
        occupied_agreement_note=inspection.occupied_agreement_note,
        offered_times=inspection.offered_times,
        general_notes=inspection.general_notes,
    )
    for item in inspection.items.all():
        copy = InspectionItem.objects.create(
            inspection=revision,
            room=item.room,
            item=item.item,
            condition=item.condition,
            notes=item.notes,
            sort_order=item.sort_order,
            prior_condition=item.prior_condition,
            prior_notes=item.prior_notes,
        )
        for photo in item.photos.all():
            photo.image.open('rb')
            content = ContentFile(photo.image.read())
            photo.image.close()
            from inspections.models import Photo
            cloned = Photo(item=copy, caption=photo.caption, taken_at=photo.taken_at)
            cloned.image.save(photo.image.name.split('/')[-1], content, save=True)
    return revision


def client_ip(request) -> str | None:
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[0].strip() or None
    return request.META.get('REMOTE_ADDR') or None


def both_reports_finalized(tenancy) -> bool:
    types = set(
        tenancy.inspections.filter(finalized_at__isnull=False).values_list('inspection_type', flat=True)
    )
    return Inspection.Type.MOVE_IN in types and Inspection.Type.MOVE_OUT in types
