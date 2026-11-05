from io import BytesIO

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from deposits.models import Deposit
from deposits.services import deposit_balance
from inspections.services import statement_bundle
from records.notices import SERVICE_LABELS


def esc(text) -> str:
    return (text or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


INK = colors.HexColor('#111111')
MUTED = colors.HexColor('#5c5c5c')
LINE = colors.HexColor('#e6e6e6')


def _styles():
    base = getSampleStyleSheet()
    base.add(ParagraphStyle(name='Cover', fontName='Times-Bold', fontSize=16, textColor=INK, leading=20, spaceAfter=8))
    base.add(ParagraphStyle(name='Section', fontName='Times-Bold', fontSize=12, textColor=INK, leading=16, spaceBefore=12, spaceAfter=6))
    base.add(ParagraphStyle(name='Body', fontName='Times-Roman', fontSize=9, textColor=INK, leading=12))
    base.add(ParagraphStyle(name='Quiet', fontName='Times-Roman', fontSize=8, textColor=MUTED, leading=11))
    return base


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(MUTED)
    canvas.setFont('Times-Roman', 8)
    canvas.drawString(0.7 * inch, 0.45 * inch, 'Not legal advice. A dispute file, not a court form.')
    canvas.drawRightString(letter[0] - 0.7 * inch, 0.45 * inch, f'Page {doc.page}')
    canvas.restoreState()


def _doc(buffer, title):
    document = SimpleDocTemplate(
        buffer, pagesize=letter,
        leftMargin=0.7 * inch, rightMargin=0.7 * inch,
        topMargin=0.7 * inch, bottomMargin=0.7 * inch,
        title=title,
    )
    return document


def _table(rows):
    table = Table(rows, colWidths=[1.6 * inch, 5.3 * inch])
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Times-Roman'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), MUTED),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LINEBELOW', (0, 0), (-1, -2), 0.25, LINE),
    ]))
    return table


def render_receipt(payment) -> bytes:
    tenancy = payment.tenancy
    prop = tenancy.unit.property
    styles = _styles()
    buffer = BytesIO()
    story = [
        Paragraph('Rent receipt', styles['Cover']),
        Paragraph(settings.NOT_LEGAL_ADVICE, styles['Quiet']),
        Spacer(1, 8),
        _table([
            ['Receipt', payment.receipt_number],
            ['Date received', payment.paid_on.isoformat()],
            ['Amount', f'${payment.amount}'],
            ['Method', payment.get_method_display()],
            ['Premises', f'{tenancy.unit.label}, {prop.street_address}, {prop.city}'],
            ['Tenant', ', '.join(person.name for person in tenancy.tenants.all())],
            ['Landlord', prop.landlord.full_name or prop.landlord.email],
            ['Note', payment.note or '—'],
        ]),
    ]
    _doc(buffer, f'Receipt {payment.receipt_number}').build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()


def render_notice_pdf(notice) -> bytes:
    styles = _styles()
    buffer = BytesIO()
    body = esc(notice.body).replace('\n', '<br/>')
    story = [
        Paragraph('Notice', styles['Cover']),
        Paragraph(settings.NOT_LEGAL_ADVICE, styles['Quiet']),
        Spacer(1, 8),
        Paragraph(body, styles['Body']),
        Spacer(1, 12),
        Paragraph(
            f'Service: {SERVICE_LABELS.get(notice.service_method, notice.service_method)}.',
            styles['Quiet'],
        ),
    ]
    _doc(buffer, 'Notice').build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()


def render_packet(tenancy) -> bytes:
    styles = _styles()
    prop = tenancy.unit.property
    buffer = BytesIO()
    story = [
        Paragraph('Tenancy record', styles['Cover']),
        Paragraph(
            f'{tenancy.unit.label}, {prop.street_address}, {prop.city}, Alberta',
            styles['Body'],
        ),
        Paragraph(settings.NOT_LEGAL_ADVICE, styles['Quiet']),
        Paragraph(
            'This file gathers the inspection summaries, deposit, rent log, notices, messages, and maintenance requests for this tenancy.',
            styles['Body'],
        ),
    ]

    story.append(Paragraph('Inspections', styles['Section']))
    inspections = list(tenancy.inspections.prefetch_related('items', 'signatures').order_by('inspection_type', 'version'))
    if not inspections:
        story.append(Paragraph('No inspection reports.', styles['Body']))
    for inspection in inspections:
        state = 'Finished' if inspection.finalized_at else 'Draft'
        story.append(Paragraph(
            f'{inspection.get_inspection_type_display()} · version {inspection.version} · {state}',
            styles['Body'],
        ))
        if inspection.conducted_on:
            story.append(Paragraph(f'Date: {inspection.conducted_on.isoformat()}', styles['Quiet']))
        statements = statement_bundle(inspection)
        story.append(Paragraph(esc(statements['vacant']), styles['Quiet']))
        presence_key = {'together': 'presence', 'refused': 'refusal', 'absent': 'absent'}.get(inspection.presence, 'presence')
        story.append(Paragraph(esc(statements[presence_key]), styles['Quiet']))
        rows = [['Room', 'Item', 'Condition', 'Move-in', 'Notes']]
        for item in inspection.items.all():
            rows.append([
                item.room, item.item, item.condition or '—',
                item.prior_condition or '—', (item.notes or '')[:80],
            ])
        if len(rows) > 1:
            table = Table(rows, colWidths=[1.2 * inch, 1.3 * inch, 1.1 * inch, 1.1 * inch, 2.2 * inch])
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Times-Roman'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#111111')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.25, LINE),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            story.append(Spacer(1, 4))
            story.append(table)
        signatures = list(inspection.signatures.all())
        if signatures:
            signed = '; '.join(f'{sig.name} ({sig.role}) {sig.signed_at.isoformat()}' for sig in signatures)
            story.append(Paragraph(signed, styles['Quiet']))

    story.append(Paragraph('Security deposit', styles['Section']))
    try:
        deposit = tenancy.deposit
    except Deposit.DoesNotExist:
        deposit = None
    if deposit is None:
        story.append(Paragraph('No deposit recorded.', styles['Body']))
    else:
        story.append(_table([
            ['Amount', f'${deposit.amount}'],
            ['Received', deposit.received_on.isoformat()],
            ['In trust', deposit.trust_deposited_on.isoformat() if deposit.trust_deposited_on else '—'],
            ['Statement sent', deposit.statement_sent_on.isoformat() if deposit.statement_sent_on else '—'],
            ['Balance', f'${deposit_balance(deposit)}'],
        ]))
        for entry in deposit.interest_entries.all():
            story.append(Paragraph(f'Interest year {entry.covers_year}: ${entry.amount} on {entry.paid_on.isoformat()}', styles['Body']))
        for entry in deposit.deductions.all():
            story.append(Paragraph(f'Deduction ({esc(entry.kind)}): ${entry.amount} — {esc(entry.reason)}', styles['Body']))

    story.append(Paragraph('Rent received', styles['Section']))
    payments = list(tenancy.payments.all())
    if not payments:
        story.append(Paragraph('No rent payments recorded.', styles['Body']))
    for payment in payments:
        story.append(Paragraph(
            f'{esc(payment.receipt_number)} · {payment.paid_on.isoformat()} · ${payment.amount} · {esc(payment.get_method_display())} · {esc(payment.note)}',
            styles['Body'],
        ))

    story.append(Paragraph('Notices', styles['Section']))
    notices = list(tenancy.notices.all())
    if not notices:
        story.append(Paragraph('No notices recorded.', styles['Body']))
    for notice in notices:
        story.append(Paragraph(esc(notice.body).replace('\n', '<br/>'), styles['Body']))
        story.append(Spacer(1, 6))

    story.append(Paragraph('Messages', styles['Section']))
    messages = list(tenancy.messages.all())
    if not messages:
        story.append(Paragraph('No messages recorded.', styles['Body']))
    for message in messages:
        story.append(Paragraph(
            f'{message.created_at.isoformat()} · {esc(message.author_name)} ({esc(message.author_role)})<br/>{esc(message.body)}',
            styles['Body'],
        ))

    story.append(Paragraph('Maintenance', styles['Section']))
    requests = list(tenancy.unit.maintenance_requests.all())
    if not requests:
        story.append(Paragraph('No maintenance requests.', styles['Body']))
    for request in requests:
        story.append(Paragraph(
            f'{request.created_at.date().isoformat()} · {esc(request.get_status_display())} · {esc(request.requester_name or request.requested_by)}<br/>{esc(request.description)}',
            styles['Body'],
        ))

    _doc(buffer, 'Tenancy record').build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
