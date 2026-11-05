import { FormEvent, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, prettyDate, Property } from '../api';
import { Shell } from '../components';

const TYPES = [
  ['house_with_suite', 'House with a suite'],
  ['room_in_home', 'Room'],
  ['duplex', 'Duplex'],
  ['condo', 'Condo'],
];

type TenantDraft = { name: string; email: string; phone: string };
type AccountLink = { name: string; email: string; path: string };

function blankTenant(): TenantDraft {
  return { name: '', email: '', phone: '' };
}

export function PropertyPage() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    street_address: '', city: '', postal_code: '', property_type: 'house_with_suite',
  });
  const [unitLabels, setUnitLabels] = useState<Record<string, string>>({});
  const [busyProperty, setBusyProperty] = useState<string | null>(null);
  const [tenantDrafts, setTenantDrafts] = useState<Record<string, TenantDraft[]>>({});
  const [notice, setNotice] = useState('');
  const [accountLinks, setAccountLinks] = useState<AccountLink[]>([]);

  async function load() {
    setProperties(await api<Property[]>('/api/properties/'));
  }

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, []);

  async function addProperty(event: FormEvent) {
    event.preventDefault();
    setError('');
    try {
      await api('/api/properties/', { method: 'POST', body: JSON.stringify({ ...form, province: 'AB' }) });
      setForm({ street_address: '', city: '', postal_code: '', property_type: 'house_with_suite' });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save the property.');
    }
  }

  async function markDone(taskId: string) {
    setError('');
    try {
      await api(`/api/maintenance-tasks/${taskId}/done/`, { method: 'POST', body: JSON.stringify({}) });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not update that task.');
    }
  }

  async function addUnit(event: FormEvent, propertyId: string) {
    event.preventDefault();
    setError('');
    setBusyProperty(propertyId);
    try {
      await api('/api/units/', {
        method: 'POST',
        body: JSON.stringify({ property: propertyId, label: unitLabels[propertyId] || 'Unit 1' }),
      });
      setUnitLabels((current) => ({ ...current, [propertyId]: 'Unit 1' }));
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not add the unit.');
    } finally {
      setBusyProperty(null);
    }
  }

  function draftsFor(unitId: string) {
    return tenantDrafts[unitId]?.length ? tenantDrafts[unitId] : [blankTenant()];
  }

  function updateDraft(unitId: string, index: number, key: keyof TenantDraft, value: string) {
    setTenantDrafts((current) => {
      const rows = [...(current[unitId]?.length ? current[unitId] : [blankTenant()])];
      rows[index] = { ...rows[index], [key]: value };
      return { ...current, [unitId]: rows };
    });
  }

  function addDraft(unitId: string) {
    setTenantDrafts((current) => ({
      ...current,
      [unitId]: [...(current[unitId]?.length ? current[unitId] : [blankTenant()]), blankTenant()],
    }));
  }

  function removeDraft(unitId: string, index: number) {
    setTenantDrafts((current) => {
      const rows = (current[unitId]?.length ? current[unitId] : [blankTenant()]).filter((_, row) => row !== index);
      return { ...current, [unitId]: rows.length ? rows : [blankTenant()] };
    });
  }

  async function refreshLink(tenantId: string) {
    setError('');
    setNotice('');
    try {
      const result = await api<AccountLink & { emailed: boolean }>(`/api/tenants/${tenantId}/account-link/`, { method: 'POST' });
      setAccountLinks([{ name: result.name, email: result.email, path: result.path }]);
      setNotice(result.emailed
        ? 'The account link was emailed. It is also shown below.'
        : 'Share this link so they can create an account.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not make an account link.');
    }
  }

  async function addTenants(event: FormEvent, tenancyId: string, unitId: string) {
    event.preventDefault();
    setError('');
    setNotice('');
    const tenants = draftsFor(unitId);
    try {
      const created = await api<{ tenants: { name: string; email: string; account_path: string }[] }>('/api/tenancies/' + tenancyId + '/tenants/', {
        method: 'POST',
        body: JSON.stringify({ tenants }),
      });
      setTenantDrafts((current) => ({ ...current, [unitId]: [blankTenant()] }));
      setAccountLinks(created.tenants.map((tenant) => ({ name: tenant.name, email: tenant.email, path: tenant.account_path })));
      setNotice('Share each link. The tenant creates their own account before they can sign in.');
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not add the tenants.');
    }
  }

  return (
    <Shell>
      <section className="page-pad stack">
        <h1>Properties</h1>
        <p className="muted">Add a property, the units you rent, and a tenant account for messages and reminders.</p>
        {error && <p className="error">{error}</p>}
        {notice && <p className="ok">{notice}</p>}
        {accountLinks.length > 0 && (
          <div className="card stack">
            {accountLinks.map((link) => (
              <p key={link.path}>{link.name} · {link.email} · <a href={link.path}>{link.path}</a></p>
            ))}
          </div>
        )}
        {properties.map((property) => (
          <article className="card stack" key={property.id}>
            <h2>{property.street_address}</h2>
            <p className="muted">{property.city}, Alberta {property.postal_code}</p>
            {property.units.map((unit) => (
              <div key={unit.id} className="stack">
                <p>{unit.label} · <Link to={`/tenancies/new?unit=${unit.id}`}>Start a tenancy</Link></p>
                {(unit.tasks || []).map((task) => (
                  <div className="row spread" key={task.id}>
                    <span>{task.label} · due {prettyDate(task.next_due_on)}</span>
                    <button className="button quiet" type="button" onClick={() => void markDone(task.id)}>Done</button>
                  </div>
                ))}
                {(unit.tenants || []).map((tenant) => (
                  <div className="row spread" key={tenant.id}>
                    <span>{tenant.name}{tenant.email ? ` · ${tenant.email}` : ''} · {tenant.has_account ? 'Account ready' : 'Needs an account'}</span>
                    {!tenant.has_account && (
                      <button className="button secondary" type="button" onClick={() => void refreshLink(tenant.id)}>Account link</button>
                    )}
                  </div>
                ))}
                {unit.current_tenancy_id ? (
                  <form className="stack" onSubmit={(event) => void addTenants(event, unit.current_tenancy_id as string, unit.id)}>
                    <h3>Add tenants</h3>
                    <p className="muted">Add everyone on this tenancy. Each person gets a link to create their own account for messages and reminders.</p>
                    {draftsFor(unit.id).map((draft, index) => (
                      <div className="stack" key={`${unit.id}-${index}`}>
                        <div className="row spread">
                          <strong>Tenant {index + 1}</strong>
                          {draftsFor(unit.id).length > 1 && (
                            <button className="button quiet" type="button" onClick={() => removeDraft(unit.id, index)}>Remove</button>
                          )}
                        </div>
                        <label>Name<input required value={draft.name} onChange={(e) => updateDraft(unit.id, index, 'name', e.target.value)} /></label>
                        <div className="grid-2">
                          <label>Email<input type="email" required value={draft.email} onChange={(e) => updateDraft(unit.id, index, 'email', e.target.value)} /></label>
                          <label>Phone<input value={draft.phone} onChange={(e) => updateDraft(unit.id, index, 'phone', e.target.value)} /></label>
                        </div>
                      </div>
                    ))}
                    <div className="row">
                      <button className="button secondary" type="button" onClick={() => addDraft(unit.id)}>Add another tenant</button>
                      <button className="button" type="submit">Save tenants</button>
                    </div>
                  </form>
                ) : (
                  <p className="muted">Start a tenancy for this unit before adding a tenant.</p>
                )}
              </div>
            ))}
            <form className="row" onSubmit={(event) => void addUnit(event, property.id)}>
              <label style={{ flex: 1 }}>Unit name
                <input value={unitLabels[property.id] ?? 'Unit 1'} onChange={(e) => setUnitLabels((current) => ({ ...current, [property.id]: e.target.value }))} />
              </label>
              <button className="button" type="submit">Add unit</button>
            </form>
          </article>
        ))}
        <form className="card stack" onSubmit={addProperty}>
          <h2>{properties.length ? 'Add a property' : 'New property'}</h2>
          <label>Street address<input required value={form.street_address} onChange={(e) => setForm({ ...form, street_address: e.target.value })} /></label>
          <div className="grid-2">
            <label>City<input required value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} /></label>
            <label>Postal code<input value={form.postal_code} onChange={(e) => setForm({ ...form, postal_code: e.target.value })} /></label>
          </div>
          <label>Property type
            <select value={form.property_type} onChange={(e) => setForm({ ...form, property_type: e.target.value })}>
              {TYPES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </label>
          <button className="button" type="submit">Save property</button>
        </form>
      </section>
    </Shell>
  );
}
