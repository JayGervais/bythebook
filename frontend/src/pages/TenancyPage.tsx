import { FormEvent, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api, Deposit, money, prettyDate, Tenancy } from '../api';
import { Shell } from '../components';
import { RecordsPanels } from './RecordsPanels';

export function NewTenancy() {
  const params = new URLSearchParams(window.location.search);
  const preset = params.get('unit') || '';
  const [units, setUnits] = useState<{ id: string; label: string; address: string }[]>([]);
  const [people, setPeople] = useState([{ name: '', email: '', phone: '' }]);
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    unit_id: preset,
    start_date: '',
    end_date: '',
    rent_amount: '',
    rent_due_day: '1',
    period: 'monthly',
    deposit_amount: '',
    deposit_received_on: '',
  });

  useEffect(() => {
    api<{ id: string; street_address: string; city: string; units: { id: string; label: string }[] }[]>('/api/properties/')
      .then((properties) => {
        const flat = properties.flatMap((property) => property.units.map((unit) => ({
          id: unit.id,
          label: unit.label,
          address: `${property.street_address}, ${property.city}`,
        })));
        setUnits(flat);
        if (!preset && flat[0]) setForm((current) => ({ ...current, unit_id: flat[0].id }));
      })
      .catch((err) => setError(err.message));
  }, [preset]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError('');
    try {
      const created = await api<Tenancy>('/api/tenancies/', {
        method: 'POST',
        body: JSON.stringify({
          unit_id: form.unit_id,
          start_date: form.start_date,
          end_date: form.end_date || null,
          rent_amount: form.rent_amount,
          rent_due_day: Number(form.rent_due_day),
          period: form.period,
          tenants: people,
          deposit_amount: form.deposit_amount || null,
          deposit_received_on: form.deposit_received_on || null,
        }),
      });
      window.location.assign(`/tenancies/${created.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save the tenancy.');
    }
  }

  return (
    <Shell>
      <section className="page-pad stack">
        <h1>New tenancy</h1>
        <p className="muted">A security deposit cannot be more than one month of rent. Leave the deposit blank if you are not taking one.</p>
        {units.length === 0 && <p className="notice">Add a property and a unit first. <Link to="/property">Go to property</Link></p>}
        <form className="card stack" onSubmit={submit}>
          <label>Unit
            <select required value={form.unit_id} onChange={(e) => setForm({ ...form, unit_id: e.target.value })}>
              {units.map((unit) => <option key={unit.id} value={unit.id}>{unit.label} — {unit.address}</option>)}
            </select>
          </label>
          <div className="grid-2">
            <label>Move-in<input type="date" required value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} /></label>
            <label>Move-out, if you know it<input type="date" value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} /></label>
          </div>
          <div className="grid-2">
            <label>Monthly rent (CAD)<input required inputMode="decimal" value={form.rent_amount} onChange={(e) => setForm({ ...form, rent_amount: e.target.value })} /></label>
            <label>Rent due day (1–28)<input required type="number" min={1} max={28} value={form.rent_due_day} onChange={(e) => setForm({ ...form, rent_due_day: e.target.value })} /></label>
          </div>
          <label>Tenancy
            <select value={form.period} onChange={(e) => setForm({ ...form, period: e.target.value })}>
              <option value="monthly">Month to month</option>
              <option value="weekly">Week to week</option>
              <option value="yearly">Year to year</option>
              <option value="fixed">Fixed term</option>
            </select>
          </label>
          {form.period === 'fixed' && <p className="muted">A fixed term ends on the move-out date. It does not need a notice to end, and the rent stays the same for the term.</p>}
          {people.map((person, index) => (
            <div className="stack" key={index}>
              <div className="row spread">
                <strong>Tenant {index + 1}</strong>
                {people.length > 1 && (
                  <button className="button quiet" type="button" onClick={() => setPeople((rows) => rows.filter((_, row) => row !== index))}>Remove</button>
                )}
              </div>
              <label>Name<input required value={person.name} onChange={(e) => setPeople((rows) => rows.map((row, i) => i === index ? { ...row, name: e.target.value } : row))} /></label>
              <div className="grid-2">
                <label>Email<input type="email" value={person.email} onChange={(e) => setPeople((rows) => rows.map((row, i) => i === index ? { ...row, email: e.target.value } : row))} /></label>
                <label>Phone<input value={person.phone} onChange={(e) => setPeople((rows) => rows.map((row, i) => i === index ? { ...row, phone: e.target.value } : row))} /></label>
              </div>
            </div>
          ))}
          <button className="button secondary" type="button" onClick={() => setPeople((rows) => [...rows, { name: '', email: '', phone: '' }])}>Add another tenant</button>
          <div className="grid-2">
            <label>Deposit amount<input inputMode="decimal" value={form.deposit_amount} onChange={(e) => setForm({ ...form, deposit_amount: e.target.value })} /></label>
            <label>Date received<input type="date" value={form.deposit_received_on} onChange={(e) => setForm({ ...form, deposit_received_on: e.target.value })} /></label>
          </div>
          {error && <p className="error">{error}</p>}
          <button className="button" type="submit">Save tenancy</button>
        </form>
      </section>
    </Shell>
  );
}

export function TenancyDetail() {
  const { id } = useParams();
  const [tenancy, setTenancy] = useState<Tenancy | null>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [invitePath, setInvitePath] = useState('');
  const [interest, setInterest] = useState({ covers_year: '1', amount: '', paid_on: '', note: '' });
  const [deduction, setDeduction] = useState({ kind: 'rent', amount: '', reason: '' });

  async function load() {
    setTenancy(await api<Tenancy>(`/api/tenancies/${id}/`));
  }

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, [id]);

  async function saveDates(event: FormEvent) {
    event.preventDefault();
    if (!tenancy) return;
    const data = new FormData(event.currentTarget as HTMLFormElement);
    try {
      setTenancy(await api<Tenancy>(`/api/tenancies/${id}/`, {
        method: 'PATCH',
        body: JSON.stringify({
          end_date: String(data.get('end_date') || '') || null,
          period: String(data.get('period') || tenancy.period),
          notice_of_landlord_on: String(data.get('notice_of_landlord_on') || '') || null,
          lease_copy_on: String(data.get('lease_copy_on') || '') || null,
        }),
      }));
      setNotice('Saved.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save.');
    }
  }

  async function saveDeposit(event: FormEvent) {
    event.preventDefault();
    const data = new FormData(event.currentTarget as HTMLFormElement);
    try {
      await api<Deposit>(`/api/tenancies/${id}/deposit/`, {
        method: 'PUT',
        body: JSON.stringify({
          amount: data.get('amount'),
          received_on: data.get('received_on'),
          trust_deposited_on: String(data.get('trust_deposited_on') || '') || null,
          statement_sent_on: String(data.get('statement_sent_on') || '') || null,
        }),
      });
      await load();
      setNotice('Deposit updated.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not update the deposit.');
    }
  }

  async function addInterest(event: FormEvent) {
    event.preventDefault();
    try {
      await api(`/api/tenancies/${id}/deposit/interest/`, { method: 'POST', body: JSON.stringify(interest) });
      setInterest({ covers_year: '1', amount: '', paid_on: '', note: '' });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not record interest.');
    }
  }

  async function addDeduction(event: FormEvent) {
    event.preventDefault();
    try {
      await api(`/api/tenancies/${id}/deposit/deductions/`, { method: 'POST', body: JSON.stringify(deduction) });
      setDeduction({ kind: 'rent', amount: '', reason: '' });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not record that deduction.');
    }
  }

  async function invite(tenantId: string) {
    setError('');
    try {
      const result = await api<{ path: string; emailed: boolean }>(`/api/tenants/${tenantId}/invite/`, { method: 'POST' });
      setInvitePath(result.path);
      setNotice(result.emailed ? 'The link was emailed. It is also copied below, in case you want to send it yourself.' : 'Copy this link. There is no email on file.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not make a link.');
    }
  }

  async function remove() {
    if (!tenancy) return;
    if (!window.confirm(`Delete the record for ${tenancy.unit_label}? Photos, signatures, and the deposit history go with it.`)) return;
    await api(`/api/tenancies/${id}/`, { method: 'DELETE' });
    window.location.assign('/home');
  }

  if (!tenancy) {
    return <Shell><section className="page-pad">{error ? <p className="error">{error}</p> : <p>Loading…</p>}</section></Shell>;
  }

  return (
    <Shell>
      <section className="page-pad stack">
        <p className="muted">{tenancy.address}</p>
        <h1>{tenancy.unit_label}</h1>
        <p>{tenancy.tenants.map((tenant) => tenant.name).join(', ')} · {money(tenancy.rent_amount)} · due on day {tenancy.rent_due_day}</p>
        {error && <p className="error">{error}</p>}
        {notice && <p className="ok">{notice}</p>}
        {invitePath && <p className="card">Tenant link: <a href={invitePath}>{invitePath}</a></p>}

        <article className="card stack">
          <h2>Inspections</h2>
          <p className="muted">Complete the move-in report within one week before or after possession, and the move-out report within one week of the tenant giving up possession. Without both finished reports, a deduction for damage is generally not available.</p>
          <ul className="list">
            {tenancy.inspections.map((inspection) => (
              <li key={inspection.id}>
                <Link className="card" to={`/inspections/${inspection.id}`}>
                  <strong>{inspection.inspection_type === 'move_in' ? 'Move-in' : 'Move-out'}</strong> · version {inspection.version}
                  <div className="muted">{inspection.is_locked ? `Finished ${prettyDate(inspection.finalized_at)}` : 'Draft'}</div>
                </Link>
              </li>
            ))}
          </ul>
        </article>

        <article className="card stack">
          <h2>Tenants</h2>
          {tenancy.tenants.map((tenant) => (
            <div key={tenant.id} className="row">
              <span>{tenant.name} {tenant.email && <span className="muted">· {tenant.email}</span>} · {tenant.has_account ? 'Account ready' : 'No account yet'}</span>
              <button className="button secondary" type="button" onClick={() => void invite(tenant.id)}>Create signing link</button>
            </div>
          ))}
        </article>

        <form className="card stack" onSubmit={saveDates}>
          <h2>Dates to remember</h2>
          <label>Tenancy
            <select name="period" defaultValue={tenancy.period}>
              <option value="monthly">Month to month</option>
              <option value="weekly">Week to week</option>
              <option value="yearly">Year to year</option>
              <option value="fixed">Fixed term</option>
            </select>
          </label>
          <label>Move-out date<input type="date" name="end_date" defaultValue={tenancy.end_date || ''} /></label>
          <label>Notice of landlord given<input type="date" name="notice_of_landlord_on" defaultValue={tenancy.notice_of_landlord_on || ''} /></label>
          <p className="muted">Hand over written notice of who the landlord is within 7 days of move-in. Confirm the current Act before you rely on the timing.</p>
          <label>Copy of the lease given<input type="date" name="lease_copy_on" defaultValue={tenancy.lease_copy_on || ''} /></label>
          <p className="muted">Give them a copy of the lease within 21 days of signing.</p>
          <button className="button" type="submit">Save dates</button>
        </form>

        <form className="card stack" onSubmit={saveDeposit}>
          <h2>Security deposit</h2>
          <p className="muted">Put it in an interest-bearing trust account, named with the words “in trust”, within two banking days. Only deposit money goes in that account.</p>
          <div className="grid-2">
            <label>Amount<input name="amount" required defaultValue={tenancy.deposit?.amount || ''} /></label>
            <label>Received<input type="date" name="received_on" required defaultValue={tenancy.deposit?.received_on || ''} /></label>
          </div>
          <div className="grid-2">
            <label>Placed in trust<input type="date" name="trust_deposited_on" defaultValue={tenancy.deposit?.trust_deposited_on || ''} /></label>
            <label>Statement sent<input type="date" name="statement_sent_on" defaultValue={tenancy.deposit?.statement_sent_on || ''} /></label>
          </div>
          {tenancy.deposit && <p>Balance after interest and deductions: {money(tenancy.deposit.balance)}</p>}
          <div className="row">
            <button className="button" type="submit">Save deposit</button>
            {tenancy.deposit && <a className="button secondary" href={`/api/tenancies/${tenancy.id}/deposit/statement.pdf`}>Download statement</a>}
          </div>
          <p>
            <a href="https://www.servicealberta.ca/interest-chart.cfm" target="_blank" rel="noreferrer">Service Alberta interest calculator</a>
          </p>
        </form>

        {tenancy.deposit && (
          <>
            <form className="card stack" onSubmit={addInterest}>
              <h2>Interest you paid</h2>
              <div className="grid-2">
                <label>Tenancy year<input type="number" min={1} value={interest.covers_year} onChange={(e) => setInterest({ ...interest, covers_year: e.target.value })} /></label>
                <label>Amount<input value={interest.amount} onChange={(e) => setInterest({ ...interest, amount: e.target.value })} /></label>
              </div>
              <label>Date paid<input type="date" required value={interest.paid_on} onChange={(e) => setInterest({ ...interest, paid_on: e.target.value })} /></label>
              <label>Note<input value={interest.note} onChange={(e) => setInterest({ ...interest, note: e.target.value })} /></label>
              <button className="button secondary" type="submit">Record interest</button>
              <ul>{tenancy.deposit.interest_entries.map((entry) => <li key={entry.id}>Year {entry.covers_year}: {money(entry.amount)} on {prettyDate(entry.paid_on)}</li>)}</ul>
            </form>
            <form className="card stack" onSubmit={addDeduction}>
              <h2>Deduction</h2>
              <p className="muted">
                {tenancy.deposit.damage_allowed
                  ? 'Both reports are finished and a copy was shared, so a damage deduction can be recorded.'
                  : 'Damage and cleaning stay locked until both inspection reports are finished and a copy has gone to the tenant. Unpaid rent can be recorded now.'}
              </p>
              <label>Kind
                <select value={deduction.kind} onChange={(e) => setDeduction({ ...deduction, kind: e.target.value })}>
                  <option value="rent">Unpaid rent</option>
                  <option value="damage">Damage or cleaning</option>
                  <option value="other">Other agreed amount</option>
                </select>
              </label>
              <label>Amount<input required value={deduction.amount} onChange={(e) => setDeduction({ ...deduction, amount: e.target.value })} /></label>
              <label>Reason<textarea required value={deduction.reason} onChange={(e) => setDeduction({ ...deduction, reason: e.target.value })} /></label>
              <button className="button secondary" type="submit">Add deduction</button>
              <ul>{tenancy.deposit.deductions.map((entry) => <li key={entry.id}>{entry.kind}: {money(entry.amount)} — {entry.reason}</li>)}</ul>
            </form>
          </>
        )}

        <RecordsPanels tenancy={tenancy} onChange={load} />

        <div className="row">
          <a className="button" href={`/api/tenancies/${tenancy.id}/packet.pdf`}>Dispute file (PDF)</a>
          <a className="button secondary" href={`/api/tenancies/${tenancy.id}/export/`}>Download the record (JSON)</a>
          <button className="button quiet" type="button" onClick={() => void remove()}>Delete this tenancy</button>
        </div>
      </section>
    </Shell>
  );
}
