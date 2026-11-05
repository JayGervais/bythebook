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

export function PropertyPage() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    street_address: '', city: '', postal_code: '', property_type: 'house_with_suite',
  });
  const [unitLabels, setUnitLabels] = useState<Record<string, string>>({});
  const [busyProperty, setBusyProperty] = useState<string | null>(null);

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

  return (
    <Shell>
      <section className="page-pad stack">
        <h1>Properties</h1>
        <p className="muted">Add a property and the units you rent.</p>
        {error && <p className="error">{error}</p>}
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
