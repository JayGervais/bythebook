import { FormEvent, useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../auth';
import { Shell } from '../components';

export function Landing() {
  const { user } = useAuth();
  const [email, setEmail] = useState('');
  const [city, setCity] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError('');
    setMessage('');
    try {
      const result = await api<{ detail: string }>('/api/waitlist/', {
        method: 'POST',
        body: JSON.stringify({ email, city }),
      });
      setMessage(result.detail);
      setEmail('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save that email.');
    }
  }

  if (user) return <Navigate to="/home" replace />;

  return (
    <Shell>
      <section className="hero">
        <p className="kicker">Alberta rental management</p>
        <h1>Inspection reports and deposit records for rental properties.</h1>
        <p className="lede">
          Record inspections, deposits, rent, notices, and maintenance for each tenancy, with the Alberta deadlines attached.
        </p>
        <div className="row">
          <Link className="button" to="/register">Create account</Link>
          <Link className="button secondary" to="/login">Sign in</Link>
        </div>
      </section>
      <section className="stack page-pad">
        <article className="card">
          <h2>Included</h2>
          <ul>
            <li>Move-in and move-out inspection reports, room by room, with photos.</li>
            <li>The statements required on an Alberta inspection report, with signatures.</li>
            <li>Deposit records: the one-month cap, the trust-account deadline, and yearly interest reminders.</li>
            <li>A signing link for the tenant. No tenant account is required.</li>
            <li>A rent log with receipts, maintenance requests, and a recurring upkeep schedule.</li>
            <li>Notice templates with Alberta timelines, and one PDF of the tenancy record.</li>
          </ul>
        </article>
        <article className="card">
          <h2>Request access</h2>
          <p className="muted">Leave an email if you manage rental property in Alberta.</p>
          <form className="stack" onSubmit={submit}>
            <label>Email<input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></label>
            <label>City<input value={city} onChange={(e) => setCity(e.target.value)} placeholder="Calgary" /></label>
            {error && <p className="error">{error}</p>}
            {message && <p className="ok">{message}</p>}
            <button className="button" type="submit">Submit</button>
          </form>
        </article>
      </section>
    </Shell>
  );
}
