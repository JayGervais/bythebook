import { FormEvent, useEffect, useState } from 'react';
import { api, money, prettyDate, Tenancy } from '../api';

type Option = { value: string; label: string };
type Catalog = {
  service_methods: Option[];
  termination_reasons: Option[];
  breach_reasons: Option[];
  kinds: Option[];
};

const emptyNotice = {
  kind: 'terminate_periodic',
  served_on: '',
  served_time: '',
  effective_on: '',
  effective_time: '',
  service_method: 'personal',
  reason_code: 'landlord_occupy',
  reason: '',
  new_rent: '',
};

export function RecordsPanels({ tenancy, onChange }: { tenancy: Tenancy; onChange: () => Promise<void> }) {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState(emptyNotice);
  const [payment, setPayment] = useState({ amount: tenancy.rent_amount, paid_on: '', method: 'etransfer', note: '' });
  const [message, setMessage] = useState('');
  const [requestText, setRequestText] = useState('');

  useEffect(() => {
    api<Catalog>('/api/notice-options/').then(setCatalog).catch((err) => setError(err.message));
  }, []);

  async function addPayment(event: FormEvent) {
    event.preventDefault();
    setError('');
    try {
      await api(`/api/tenancies/${tenancy.id}/payments/`, { method: 'POST', body: JSON.stringify(payment) });
      setPayment({ amount: tenancy.rent_amount, paid_on: '', method: 'etransfer', note: '' });
      await onChange();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not record that payment.');
    }
  }

  async function addNotice(event: FormEvent) {
    event.preventDefault();
    setError('');
    const payload: Record<string, string | null> = {
      kind: notice.kind,
      served_on: notice.served_on,
      effective_on: notice.effective_on,
      service_method: notice.service_method,
      reason_code: notice.reason_code,
      reason: notice.reason,
      served_time: notice.served_time || null,
      effective_time: notice.effective_time || null,
      new_rent: notice.kind === 'rent_increase' ? notice.new_rent : null,
    };
    try {
      await api(`/api/tenancies/${tenancy.id}/notices/`, { method: 'POST', body: JSON.stringify(payload) });
      setNotice(emptyNotice);
      await onChange();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save that notice.');
    }
  }

  async function applyIncrease(id: string) {
    setError('');
    try {
      await api(`/api/tenancies/${tenancy.id}/notices/${id}/apply/`, { method: 'POST' });
      await onChange();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not update the rent.');
    }
  }

  async function addMessage(event: FormEvent) {
    event.preventDefault();
    setError('');
    try {
      await api(`/api/tenancies/${tenancy.id}/messages/`, { method: 'POST', body: JSON.stringify({ body: message }) });
      setMessage('');
      await onChange();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save that message.');
    }
  }

  async function addRequest(event: FormEvent) {
    event.preventDefault();
    setError('');
    try {
      await api(`/api/units/${tenancy.unit}/requests/`, {
        method: 'POST',
        body: JSON.stringify({ description: requestText, tenancy: tenancy.id }),
      });
      setRequestText('');
      await onChange();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save that request.');
    }
  }

  async function setStatus(id: string, status: string) {
    setError('');
    try {
      await api(`/api/maintenance-requests/${id}/`, { method: 'PATCH', body: JSON.stringify({ status }) });
      await onChange();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not update that request.');
    }
  }

  const needsTime = notice.kind === 'entry' || notice.kind === 'damage_or_assault';

  return (
    <>
      {error && <p className="error">{error}</p>}

      <article className="card stack">
        <h2>Rent received</h2>
        <p className="muted">Record each payment yourself. e-Transfer is the usual method. Nothing is collected through the app.</p>
        <ul>
          {tenancy.payments.map((row) => (
            <li key={row.id}>
              {row.receipt_number} · {prettyDate(row.paid_on)} · {money(row.amount)} · {row.method_label}
              {row.note ? ` · ${row.note}` : ''} · <a href={`/api/tenancies/${tenancy.id}/payments/${row.id}/receipt.pdf`}>Receipt</a>
            </li>
          ))}
        </ul>
        <form className="stack" onSubmit={addPayment}>
          <div className="grid-2">
            <label>Amount<input required value={payment.amount} onChange={(e) => setPayment({ ...payment, amount: e.target.value })} /></label>
            <label>Date received<input type="date" required value={payment.paid_on} onChange={(e) => setPayment({ ...payment, paid_on: e.target.value })} /></label>
          </div>
          <div className="grid-2">
            <label>Method
              <select value={payment.method} onChange={(e) => setPayment({ ...payment, method: e.target.value })}>
                <option value="etransfer">e-Transfer</option>
                <option value="cash">Cash</option>
                <option value="cheque">Cheque</option>
                <option value="other">Other</option>
              </select>
            </label>
            <label>Note<input value={payment.note} onChange={(e) => setPayment({ ...payment, note: e.target.value })} /></label>
          </div>
          <button className="button secondary" type="submit">Record payment</button>
        </form>
      </article>

      <article className="card stack">
        <h2>Notices</h2>
        <p className="muted">
          Dates follow the Residential Tenancies Act for this tenancy.
          The served date is the date service was effected, by personal service or registered mail unless the Act allows another method.
          This is not a government form.
        </p>
        {tenancy.notices.map((row) => (
          <div key={row.id} className="stack">
            <p><strong>{catalog?.kinds.find((item) => item.value === row.kind)?.label || row.kind}</strong> · served {prettyDate(row.served_on)} · effective {prettyDate(row.effective_on)}</p>
            <p className="muted" style={{ whiteSpace: 'pre-wrap' }}>{row.body}</p>
            <div className="row">
              <a className="button secondary" href={`/api/tenancies/${tenancy.id}/notices/${row.id}/pdf/`}>Download</a>
              {row.kind === 'rent_increase' && <button className="button secondary" type="button" onClick={() => void applyIncrease(row.id)}>Set this as the current rent</button>}
            </div>
          </div>
        ))}
        {catalog && (
          <form className="stack" onSubmit={addNotice}>
            <label>Notice
              <select value={notice.kind} onChange={(e) => setNotice({ ...notice, kind: e.target.value })}>
                {catalog.kinds.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
              </select>
            </label>
            <div className="grid-2">
              <label>Served<input type="date" required value={notice.served_on} onChange={(e) => setNotice({ ...notice, served_on: e.target.value })} /></label>
              <label>Effective<input type="date" required value={notice.effective_on} onChange={(e) => setNotice({ ...notice, effective_on: e.target.value })} /></label>
            </div>
            {needsTime && (
              <div className="grid-2">
                <label>Time served<input type="time" required value={notice.served_time} onChange={(e) => setNotice({ ...notice, served_time: e.target.value })} /></label>
                <label>Time effective<input type="time" required value={notice.effective_time} onChange={(e) => setNotice({ ...notice, effective_time: e.target.value })} /></label>
              </div>
            )}
            <label>How it was served
              <select value={notice.service_method} onChange={(e) => setNotice({ ...notice, service_method: e.target.value })}>
                {catalog.service_methods.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
              </select>
            </label>
            {notice.kind === 'terminate_periodic' && (
              <label>Reason
                <select value={notice.reason_code} onChange={(e) => setNotice({ ...notice, reason_code: e.target.value })}>
                  {catalog.termination_reasons.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
                </select>
              </label>
            )}
            {notice.kind === 'substantial_breach' && (
              <label>Breach
                <select value={notice.reason_code} onChange={(e) => setNotice({ ...notice, reason_code: e.target.value })}>
                  {catalog.breach_reasons.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
                </select>
              </label>
            )}
            {notice.kind === 'rent_increase' && (
              <label>New rent<input required value={notice.new_rent} onChange={(e) => setNotice({ ...notice, new_rent: e.target.value })} /></label>
            )}
            {notice.kind !== 'rent_increase' && (
              <label>Details<textarea value={notice.reason} onChange={(e) => setNotice({ ...notice, reason: e.target.value })} /></label>
            )}
            <button className="button secondary" type="submit">Save notice</button>
          </form>
        )}
      </article>

      <article className="card stack">
        <h2>Messages</h2>
        <ul>
          {tenancy.messages.map((row) => (
            <li key={row.id}><strong>{row.author_name}</strong> · {row.body}</li>
          ))}
        </ul>
        <form className="stack" onSubmit={addMessage}>
          <label>Add a note<textarea required value={message} onChange={(e) => setMessage(e.target.value)} /></label>
          <button className="button secondary" type="submit">Save message</button>
        </form>
      </article>

      <article className="card stack">
        <h2>Maintenance</h2>
        <ul>
          {tenancy.maintenance_requests.map((row) => (
            <li key={row.id}>
              {row.description} · {row.status.replace('_', ' ')} · {row.requester_name}
              <div className="row">
                {row.status !== 'in_progress' && <button className="button quiet" type="button" onClick={() => void setStatus(row.id, 'in_progress')}>In progress</button>}
                {row.status !== 'resolved' && <button className="button quiet" type="button" onClick={() => void setStatus(row.id, 'resolved')}>Resolved</button>}
              </div>
            </li>
          ))}
        </ul>
        <form className="stack" onSubmit={addRequest}>
          <label>Request<textarea required value={requestText} onChange={(e) => setRequestText(e.target.value)} /></label>
          <button className="button secondary" type="submit">Add request</button>
        </form>
      </article>
    </>
  );
}
