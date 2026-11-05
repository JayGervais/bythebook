import { FormEvent, useEffect, useState } from 'react';
import { api, prettyDate, TenancyMessage } from '../api';
import { Shell } from '../components';

type TenantReminder = {
  id: string;
  kind: string;
  due_on: string;
  headline: string;
  detail: string;
  unit: string;
};

type TenantHomeData = {
  name: string;
  address: string;
  unit: string;
  messages: TenancyMessage[];
  reminders: TenantReminder[];
};

export function TenantHome() {
  const [home, setHome] = useState<TenantHomeData | null>(null);
  const [note, setNote] = useState('');
  const [error, setError] = useState('');

  async function load() {
    setHome(await api<TenantHomeData>('/api/tenant/home/'));
  }

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, []);

  async function send(event: FormEvent) {
    event.preventDefault();
    setError('');
    try {
      await api('/api/tenant/messages/', { method: 'POST', body: JSON.stringify({ body: note }) });
      setNote('');
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not send that message.');
    }
  }

  return (
    <Shell>
      <section className="page-pad stack">
        <h1>{home?.name || 'Your tenancy'}</h1>
        <p className="muted">{home ? `${home.unit} · ${home.address}` : 'Messages and reminders for your rental.'}</p>
        {error && <p className="error">{error}</p>}
        {home && (
          <>
            <div className="stack">
              {home.reminders.length === 0 && <p className="card">No open reminders.</p>}
              {home.reminders.length > 0 && <p className="section-label">Reminders</p>}
              {home.reminders.map((reminder) => (
                <article className="card" key={reminder.id}>
                  <p className="due-meta">{reminder.unit} · due {prettyDate(reminder.due_on)}</p>
                  <h2>{reminder.headline}</h2>
                  <p>{reminder.detail}</p>
                </article>
              ))}
            </div>
            <article className="card stack">
              <h2>Messages</h2>
              {home.messages.length === 0 && <p className="muted">No messages yet.</p>}
              <ul className="list">
                {home.messages.map((row) => (
                  <li key={row.id}><strong>{row.author_name}:</strong> {row.body}</li>
                ))}
              </ul>
              <form className="stack" onSubmit={(event) => void send(event)}>
                <label>Message<textarea required value={note} onChange={(e) => setNote(e.target.value)} /></label>
                <button className="button" type="submit">Send</button>
              </form>
            </article>
          </>
        )}
      </section>
    </Shell>
  );
}
