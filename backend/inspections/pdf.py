from io import BytesIO

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from deposits.services import deposit_balance
from inspections.services import statement_bundle


INK = colors.HexColor('#1f2a24')
GREEN = colors.HexColor('#234e3a')
RULE = colors.HexColor('#d9d0c3')
PAPER = colors.HexColor('#f7f3ec')


def _styles():
    base = getSampleStyleSheet()
    base.add(ParagraphStyle(
        name='Cover', fontName='Times-Bold', fontSize=18, textColor=GREEN, leading=22, spaceAfter=6,
    ))
    base.add(ParagraphStyle(
        name='Quiet', fontName='Times-Roman', fontSize=9, textColor=colors.HexColor('#5c564c'), leading=12,
    ))
    base.add(ParagraphStyle(
        name='Body', fontName='Times-Roman', fontSize=10, textColor=INK, leading=14,
    ))
    base.add(ParagraphStyle(
        name='Cell', fontName='Times-Roman', fontSize=8, textColor=INK, leading=11,
    ))
    base.add(ParagraphStyle(
        name='Head', fontName='Times-Bold', fontSize=8, textColor=colors.white, leading=11,
    ))
    return base


def _footer(canvas, doc):
    canvas.saveState()
    inspection = getattr(doc, 'inspection', None)
    if inspection is not None and inspection.finalized_at is None:
        canvas.setFillColor(colors.Color(0.55, 0.25, 0.12, alpha=0.15))
        canvas.setFont('Times-Bold', 64)
        canvas.translate(letter[0] / 2, letter[1] / 2)
        canvas.rotate(32)
        canvas.drawCentredString(0, 0, 'DRAFT')
        canvas.rotate(-32)
        canvas.translate(-letter[0] / 2, -letter[1] / 2)
    canvas.setFillColor(colors.HexColor('#5c564c'))
    canvas.setFont('Times-Roman', 8)
    canvas.drawString(0.7 * inch, 0.42 * inch, 'Not legal advice. Keep a copy for at least three years after the tenancy ends.')
    canvas.drawRightString(letter[0] - 0.7 * inch, 0.42 * inch, f'Page {doc.page}')
    canvas.restoreState()


def _condition_label(code: str) -> str:
    labels = {
        'good': 'Good',
        'fair': 'Fair',
        'poor': 'Poor',
        'damaged': 'Damaged',
        'not_applicable': 'Not applicable',
    }
    return labels.get(code, '—')


def render_inspection_pdf(inspection) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        leftMargin=0.7 * inch, rightMargin=0.7 * inch,
        topMargin=0.7 * inch, bottomMargin=0.7 * inch,
        title='Inspection report',
    )
    doc.inspection = inspection
    styles = _styles()
    tenancy = inspection.tenancy
    unit = tenancy.unit
    prop = unit.property
    tenants = ', '.join(tenancy.tenants.values_list('name', flat=True)) or '—'
    kind = 'Move-in' if inspection.inspection_type == 'move_in' else 'Move-out'
    story = [
        Paragraph('By the Book', styles['Quiet']),
        Paragraph(f'{kind} inspection report', styles['Cover']),
        Paragraph(settings.NOT_LEGAL_ADVICE, styles['Quiet']),
        Spacer(1, 8),
        Paragraph(f'<b>Premises.</b> {prop.street_address}, {prop.city}, Alberta {prop.postal_code}', styles['Body']),
        Paragraph(f'<b>Unit.</b> {unit.label}', styles['Body']),
        Paragraph(f'<b>Tenant.</b> {tenants}', styles['Body']),
        Paragraph(
            f'<b>Tenancy.</b> {tenancy.start_date.isoformat()}'
            + (f' to {tenancy.end_date.isoformat()}' if tenancy.end_date else ''),
            styles['Body'],
        ),
        Paragraph(
            f'<b>Inspection date.</b> {inspection.conducted_on.isoformat() if inspection.conducted_on else "Not set"}'
            f' · version {inspection.version}',
            styles['Body'],
        ),
    ]
    if inspection.occupied_agreement_note:
        story.append(Paragraph(
            f'<b>Occupied by agreement.</b> {inspection.occupied_agreement_note}',
            styles['Body'],
        ))
    if inspection.general_notes:
        story.append(Paragraph(f'<b>Notes.</b> {inspection.general_notes}', styles['Body']))
    story.append(Spacer(1, 10))

    move_out = inspection.inspection_type == 'move_out'
    header = ['Room', 'Item', 'Move-in', 'Now', 'Notes'] if move_out else ['Room', 'Item', 'Condition', 'Notes']
    data = [[Paragraph(cell, styles['Head']) for cell in header]]
    for item in inspection.items.all():
        notes = item.notes or ''
        if move_out:
            row = [
                item.room, item.item,
                _condition_label(item.prior_condition),
                _condition_label(item.condition),
                notes,
            ]
        else:
            row = [item.room, item.item, _condition_label(item.condition), notes]
        data.append([Paragraph(cell, styles['Cell']) for cell in row])
    if len(data) == 1:
        data.append([Paragraph('No items yet.', styles['Cell'])] + [Paragraph('', styles['Cell'])] * (len(header) - 1))
    col_widths = [1.15 * inch, 1.45 * inch, 0.9 * inch, 0.9 * inch, 2.5 * inch] if move_out else [1.3 * inch, 1.7 * inch, 1.2 * inch, 2.7 * inch]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), GREEN),
        ('BACKGROUND', (0, 1), (-1, -1), PAPER),
        ('GRID', (0, 0), (-1, -1), 0.3, RULE),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(table)
    story.append(Spacer(1, 12))

    for item in inspection.items.prefetch_related('photos'):
        for photo in item.photos.all():
            story.append(Paragraph(f'{item.room} — {item.item}. {photo.caption}', styles['Quiet']))
            try:
                photo.image.open('rb')
                raw = BytesIO(photo.image.read())
                photo.image.close()
                story.append(Image(raw, width=2.4 * inch, height=1.8 * inch))
                story.append(Spacer(1, 6))
            except OSError:
                story.append(Paragraph('Photo could not be embedded.', styles['Quiet']))

    bundle = statement_bundle(inspection)
    story.append(Spacer(1, 8))
    story.append(Paragraph(bundle['vacant'], styles['Body']))
    story.append(Spacer(1, 8))
    signatures = {sig.role: sig for sig in inspection.signatures.all()}
    blocks = []
    if inspection.presence in ('together', 'refused'):
        blocks.append(('landlord_presence', bundle['presence']))
    if inspection.presence == 'together':
        if 'tenant_disagree' in signatures or inspection.disagreement_reasons:
            text = bundle['disagree']
            if inspection.disagreement_reasons:
                text += ' ' + inspection.disagreement_reasons
            blocks.append(('tenant_disagree', text))
        else:
            blocks.append(('tenant_agree', bundle['agree']))
    if inspection.presence == 'refused':
        blocks.append(('landlord_refusal', bundle['refusal']))
    if inspection.presence == 'absent':
        blocks.append(('landlord_absent', bundle['absent']))
        for offer in inspection.offered_times or []:
            story.append(Paragraph(
                f"Offered {offer.get('date', '')} at {offer.get('time', '')}.",
                styles['Quiet'],
            ))
    for role, text in blocks:
        story.append(Paragraph(text, styles['Body']))
        sig = signatures.get(role)
        if sig is not None:
            story.append(Paragraph(
                f'Signed by {sig.name} on {sig.signed_at.strftime("%Y-%m-%d %H:%M %Z")}.',
                styles['Quiet'],
            ))
            try:
                sig.image.open('rb')
                raw = BytesIO(sig.image.read())
                sig.image.close()
                story.append(Image(raw, width=2.2 * inch, height=0.8 * inch))
            except OSError:
                pass
        story.append(Spacer(1, 8))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()


def render_deposit_statement(deposit) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        leftMargin=0.7 * inch, rightMargin=0.7 * inch,
        topMargin=0.7 * inch, bottomMargin=0.7 * inch,
        title='Deposit statement',
    )
    styles = _styles()
    tenancy = deposit.tenancy
    prop = tenancy.unit.property
    story = [
        Paragraph('By the Book', styles['Quiet']),
        Paragraph('Security deposit statement', styles['Cover']),
        Paragraph(settings.NOT_LEGAL_ADVICE, styles['Quiet']),
        Spacer(1, 8),
        Paragraph(f'{prop.street_address}, {prop.city} · {tenancy.unit.label}', styles['Body']),
        Paragraph(f'Deposit received {deposit.received_on.isoformat()}: ${deposit.amount}', styles['Body']),
    ]
    if deposit.trust_deposited_on:
        story.append(Paragraph(f'Placed in trust on {deposit.trust_deposited_on.isoformat()}.', styles['Body']))
    for entry in deposit.interest_entries.all():
        story.append(Paragraph(
            f'Interest for year {entry.covers_year}, paid {entry.paid_on.isoformat()}: ${entry.amount}. {entry.note}',
            styles['Body'],
        ))
    for entry in deposit.deductions.all():
        story.append(Paragraph(f'{entry.get_kind_display()}: ${entry.amount}. {entry.reason}', styles['Body']))
    story.append(Spacer(1, 8))
    story.append(Paragraph(f'<b>Balance.</b> ${deposit_balance(deposit)}', styles['Body']))
    if deposit.statement_sent_on:
        story.append(Paragraph(f'Statement marked sent on {deposit.statement_sent_on.isoformat()}.', styles['Quiet']))
    doc.inspection = None
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
