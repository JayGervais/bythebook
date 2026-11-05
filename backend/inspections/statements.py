"""Wording from section 4 of the Residential Tenancies Ministerial Regulation.

These strings are the statements the regulation says an inspection report must
contain. They are not a substitute for reading the current regulation.
"""

VACANT_STATEMENT = (
    'Inspections should be conducted when the premises are vacant unless the '
    'landlord and tenant or their agents otherwise agree.'
)

REFUSAL_STATEMENT = (
    "The tenant or tenant's agent present at the inspection refused to sign the tenant's statement."
)


def presence_statement(conducted_on: str, landlord_name: str, tenant_name: str) -> str:
    return (
        f'The inspection of the premises was conducted on {conducted_on} by {landlord_name} '
        f'and by {tenant_name}.'
    )


def agree_statement(name: str) -> str:
    return f'I, {name}, agree that this report fairly represents the condition of the premises.'


def disagree_statement(name: str) -> str:
    return (
        f'I, {name}, disagree that this report fairly represents the condition of the premises '
        'for the following reasons:'
    )


def absent_statement(conducted_on: str, landlord_name: str) -> str:
    return (
        f'The inspection of the premises was conducted on {conducted_on} by {landlord_name} '
        "without the tenant or the tenant's agent being present."
    )
