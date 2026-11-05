import { FormEvent, useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { api, User } from '../api';
import { useAuth } from '../auth';
import { Shell } from '../components';

export function Login() {
  const { user, setUser } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  if (user) return <Navigate to="/property" replace />;

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError('');
    try {
      setUser(await api<User>('/api/auth/login/', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }));
      navigate('/home');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not sign in.');
    }
  }

  return (
    <Shell>
      <section className="page-pad stack">
        <h1>Sign in</h1>
        <form className="card stack" onSubmit={submit}>
          <label>Email<input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></label>
          <label>Password<input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} /></label>
          {error && <p className="error">{error}</p>}
          <button className="button" type="submit">Sign in</button>
          <p className="muted">No account yet? <Link to="/register">Create an account</Link></p>
        </form>
      </section>
    </Shell>
  );
}

export function Register() {
  const { user, setUser } = useAuth();
  const [form, setForm] = useState({
    email: '', password: '', full_name: '', phone: '', address_for_service: '',
  });
  const [error, setError] = useState('');

  if (user) return <Navigate to="/home" replace />;

  function set<K extends keyof typeof form>(key: K, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError('');
    try {
      setUser(await api<User>('/api/auth/register/', { method: 'POST', body: JSON.stringify(form) }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create the account.');
    }
  }

  return (
    <Shell>
      <section className="page-pad stack">
        <h1>Create account</h1>
        <p className="muted">Landlord accounts manage properties and tenancies. Tenants sign reports from a link.</p>
        <form className="card stack" onSubmit={submit}>
          <label>Name<input required value={form.full_name} onChange={(e) => set('full_name', e.target.value)} /></label>
          <label>Email<input type="email" required value={form.email} onChange={(e) => set('email', e.target.value)} /></label>
          <label>Password<input type="password" required value={form.password} onChange={(e) => set('password', e.target.value)} /></label>
          <label>Phone<input value={form.phone} onChange={(e) => set('phone', e.target.value)} /></label>
          <label>Address for service<textarea value={form.address_for_service} onChange={(e) => set('address_for_service', e.target.value)} /></label>
          {error && <p className="error">{error}</p>}
          <button className="button" type="submit">Create account</button>
        </form>
      </section>
    </Shell>
  );
}
