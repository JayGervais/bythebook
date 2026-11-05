import { FormEvent, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api, User } from '../api';
import { useAuth } from '../auth';
import { Shell } from '../components';

type Invite = {
  name: string;
  email: string;
  address: string;
  unit: string;
  has_account: boolean;
};

export function JoinPage() {
  const { token } = useParams();
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const [invite, setInvite] = useState<Invite | null>(null);
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    api<Invite>(`/api/join/${token}/`)
      .then(setInvite)
      .catch((err) => setError(err.message));
  }, [token]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError('');
    if (password !== confirm) {
      setError('Those passwords do not match.');
      return;
    }
    try {
      setUser(await api<User>(`/api/join/${token}/`, {
        method: 'POST',
        body: JSON.stringify({ password }),
      }));
      navigate('/home');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create the account.');
    }
  }

  return (
    <Shell>
      <section className="page-pad stack">
        <h1>Create your account</h1>
        {error && <p className="error">{error}</p>}
        {!invite && !error && <p>Loading…</p>}
        {invite && (
          <>
            <p className="muted">{invite.name} · {invite.unit} at {invite.address}</p>
            {invite.has_account ? (
              <p className="card">This account is already set up. <Link to="/login">Sign in</Link> with {invite.email}.</p>
            ) : (
              <form className="card stack" onSubmit={(event) => void submit(event)}>
                <p>Choose a password for {invite.email}. You will use it to see reminders and send messages.</p>
                <label>Password<input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} /></label>
                <label>Confirm password<input type="password" required value={confirm} onChange={(e) => setConfirm(e.target.value)} /></label>
                <button className="button" type="submit">Create account</button>
              </form>
            )}
          </>
        )}
      </section>
    </Shell>
  );
}
