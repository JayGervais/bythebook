import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, MaintenanceTask, prettyDate, Reminder, Tenancy } from '../api';
import { useAuth } from '../auth';
import { Shell } from '../components';

type Home = {
  disclaimer: string;
  reminders: Reminder[];
  tenancies: Tenancy[];
  maintenance: MaintenanceTask[];
};

export function HomePage() {
  const { user } = useAuth();
  const [home, setHome] = useState<Home | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api<Home>('/api/home/').then(setHome).catch((err) => setError(err.message));
  }, []);

  return (
    <Shell>
      <section className="page-pad stack">
        <h1>{user ? user.full_name : 'Overview'}</h1>
        <p className="muted">Open deadlines across your properties.</p>
        {error && <p className="error">{error}</p>}
        {home && (
          <>
            <div className="stack">
              {home.reminders.length === 0 && <p className="card">No open deadlines. Add a tenancy to track inspections and the deposit.</p>}
              {home.reminders.length > 0 && <p className="section-label">Due soon</p>}
              {home.reminders.map((reminder) => (
                <Link key={reminder.id} className="card" to={`/tenancies/${reminder.tenancy_id}`}>
                  <p className="due-meta">{reminder.unit} · due {prettyDate(reminder.due_on)}</p>
                  <h2>{reminder.headline}</h2>
                  <p>{reminder.detail}</p>
                </Link>
              ))}
            </div>
            {home.maintenance.length > 0 && (
              <div className="stack">
                <p className="section-label">Maintenance</p>
                {home.maintenance.map((task) => (
                  <Link key={task.id} className="card" to="/property">
                    <p className="task-meta">{task.unit_label} · due {prettyDate(task.next_due_on)}</p>
                    <h3>{task.label}</h3>
                    <p>{task.note}</p>
                  </Link>
                ))}
              </div>
            )}
            <div className="row">
              <Link className="button" to="/property">Properties</Link>
              <Link className="button secondary" to="/tenancies/new">New tenancy</Link>
            </div>
            <ul className="list">
              {home.tenancies.map((tenancy) => (
                <li key={tenancy.id}>
                  <Link className="card" to={`/tenancies/${tenancy.id}`}>
                    <h3>{tenancy.unit_label} <span className="pill">{tenancy.status}</span></h3>
                    <p className="muted">{tenancy.address} · {tenancy.tenants.map((t) => t.name).join(', ')}</p>
                  </Link>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>
    </Shell>
  );
}
