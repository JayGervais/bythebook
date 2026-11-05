"""Notice text. Wording follows the Act's required contents. It is not a government form."""

from datetime import date, time

PERIOD_LABELS = {
    'weekly': 'Week to week',
    'monthly': 'Month to month',
    'yearly': 'Year to year',
    'fixed': 'Fixed term',
}

SERVICE_LABELS = {
    'personal': 'Personal service',
    'registered_mail': 'Registered mail',
    'adult_resident': 'Left with an adult who lives there, after the tenant could not be served',
    'posted': 'Posted on the premises, after the tenant could not be served',
    'electronic': 'Electronic, to an address the person gave for service',
}

TERMINATION_REASONS = {
    'landlord_occupy': 'The landlord, or a relative of the landlord, intends to occupy the premises.',
    'purchaser_occupy': 'The premises have been sold, and the purchaser or a relative of the purchaser intends to occupy them.',
    'demolish': 'The landlord intends to demolish the building.',
    'renovate': 'The landlord intends major repairs or renovations that require the premises to be vacant.',
    'other': '',
}

BREACH_REASONS = {
    'nonpayment': 'The tenant has not paid the rent that is due.',
    'other': '',
}


def catalog():
    return {
        'periods': [{'value': key, 'label': label} for key, label in PERIOD_LABELS.items()],
        'service_methods': [{'value': key, 'label': label} for key, label in SERVICE_LABELS.items()],
        'termination_reasons': [
            {'value': key, 'label': label or 'Another prescribed reason, written out below'}
            for key, label in TERMINATION_REASONS.items()
        ],
        'breach_reasons': [
            {'value': 'nonpayment', 'label': 'Unpaid rent'},
            {'value': 'other', 'label': 'Another substantial breach'},
        ],
        'kinds': [
            {'value': 'terminate_periodic', 'label': 'End a periodic tenancy'},
            {'value': 'substantial_breach', 'label': 'Substantial breach (14 days)'},
            {'value': 'damage_or_assault', 'label': 'Significant damage or assault (24 hours)'},
            {'value': 'rent_increase', 'label': 'Rent increase'},
            {'value': 'entry', 'label': 'Notice of entry'},
        ],
    }


def _premises(tenancy) -> str:
    unit = tenancy.unit
    prop = unit.property
    return f'{unit.label}, {prop.street_address}, {prop.city}, Alberta {prop.postal_code}'.strip()


def _when(day: date, at: time | None) -> str:
    text = day.strftime('%B %d, %Y').replace(' 0', ' ')
    if at:
        text += f' at {at.strftime("%I:%M %p").lstrip("0")}'
    return text


def render_notice(notice) -> str:
    tenancy = notice.tenancy
    landlord = tenancy.unit.property.landlord
    tenants = ', '.join(person.name for person in tenancy.tenants.all()) or 'The tenant'
    premises = _premises(tenancy)
    served = _when(notice.served_on, notice.served_time)
    effective = _when(notice.effective_on, notice.effective_time)
    method = SERVICE_LABELS.get(notice.service_method, notice.service_method)
    landlord_name = landlord.full_name or landlord.email

    if notice.kind == 'terminate_periodic':
        reason = TERMINATION_REASONS.get(notice.reason_code) or notice.reason
        return (
            f'Notice to the tenant to end a periodic tenancy\n\n'
            f'To: {tenants}\n'
            f'Premises: {premises}\n'
            f'From: {landlord_name}\n\n'
            f'This notice ends the {PERIOD_LABELS.get(tenancy.period, tenancy.period).lower()} tenancy '
            f'on {effective}.\n\n'
            f'Reason: {reason}\n\n'
            f'A landlord may end a periodic tenancy only for a reason the Residential Tenancies Act '
            f'or its regulations prescribe, including sections 11 and 12 where they apply. '
            f'If the tenant moves out and the premises are not used for the reason in this notice '
            f'within a reasonable time, the landlord can be in breach of the Act.\n\n'
            f'Served {served} by {method.lower()}.'
        )

    if notice.kind == 'substantial_breach':
        reason = notice.reason.strip()
        pay = ''
        if notice.reason_code == 'nonpayment':
            pay = (
                '\n\nThis tenancy will not end if, on or before the termination date, the tenant pays '
                'the rent due as of the date of this notice and any additional rent that has become due '
                'by the date of payment.'
            )
        return (
            f'Notice to terminate for substantial breach\n\n'
            f'To: {tenants}\n'
            f'Premises: {premises}\n'
            f'From: {landlord_name}\n\n'
            f'The tenancy will terminate on {effective}, which is at least 14 days after this notice.\n\n'
            f'Rent due as of this notice: see the reason below.\n'
            f'Additional rent that may become due before the termination date: the regular rent if another due date falls inside the notice period.\n\n'
            f'Reason: {reason}{pay}\n\n'
            f'If the breach is something other than unpaid rent, this notice has no effect if the tenant '
            f'serves a written objection, with reasons, before the termination date.\n\n'
            f'Served {served} by {method.lower()}.'
        )

    if notice.kind == 'damage_or_assault':
        return (
            f'Notice to terminate for significant damage, assault, or threat\n\n'
            f'To: {tenants}\n'
            f'Premises: {premises}\n'
            f'From: {landlord_name}\n\n'
            f'The tenancy will terminate on {effective}.\n\n'
            f'Reason: {notice.reason.strip()}\n\n'
            f'This notice is for significant damage to the premises, common areas, or property, '
            f'or for a physical assault or threat of physical assault against the landlord or another tenant. '
            f'It has to be served at least 24 hours before that time. If the tenant does not leave, '
            f'the landlord has 10 days to apply to the court to confirm the termination. '
            f'Without that application, the notice can cease to have effect.\n\n'
            f'Served {served} by {method.lower()}.'
        )

    if notice.kind == 'rent_increase':
        return (
            f'Notice of rent increase\n\n'
            f'To: {tenants}\n'
            f'Premises: {premises}\n'
            f'From: {landlord_name}\n\n'
            f'The rent will increase to ${notice.new_rent} on {effective}.\n\n'
            f'The current rent is ${tenancy.rent_amount}, due on day {tenancy.rent_due_day} of the tenancy period. '
            f'A periodic tenancy needs written notice of at least 12 tenancy weeks, 3 tenancy months, or 90 days, '
            f'depending on the period. Rent cannot go up until 365 days after the tenancy started or after the last increase, '
            f'and it cannot go up during a fixed term.\n\n'
            f'Served {served} by {method.lower()}.\n'
            f'Signed: {landlord_name}'
        )

    return (
        f'Notice of entry\n\n'
        f'To: {tenants}\n'
        f'Premises: {premises}\n'
        f'From: {landlord_name}\n\n'
        f'The landlord will enter on {effective}.\n\n'
        f'Reason: {notice.reason.strip()}\n\n'
        f'Entry with notice is for inspection, repairs, pest control, or showing the premises. '
        f'The notice has to be served at least 24 hours ahead, name a date and time between 8:00 a.m. and 8:00 p.m., '
        f'and avoid a holiday or a Sunday unless the tenant has named a different day of worship.\n\n'
        f'Served {served} by {method.lower()}.\n'
        f'Signed: {landlord_name}'
    )
