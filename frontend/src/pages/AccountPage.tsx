import { FormEvent, useState } from 'react';
import { api, User } from '../api';
import { useAuth } from '../auth';
import { Shell } from '../components';

export function AccountPage() {
  const { user, setUser } = useAuth();
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  if (!user) return null;

  async function submit(event: FormEvent) {
    event.preventDefault();
    const data = new FormData(event.currentTarget as HTMLFormElement);
    try {
      setUser(await api<User>('/api/auth/me/', {
        method: 'PATCH',
        body: JSON.stringify({
          full_name: data.get('full_name'),
          phone: data.get('phone'),
          address_for_service: data.get('address_for_service'),
        }),
      }));
      setNotice('Saved.');
      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save.');
    }
  }

  return (
    <Shell>
      <section className="page-pad stack">
        <h1>Your account</h1>
        <form className="card stack" onSubmit={submit}>
          <label>Name<input name="full_name" defaultValue={user.full_name} /></label>
          <label>Email<input value={user.email} disabled /></label>
          <label>Phone<input name="phone" defaultValue={user.phone} /></label>
          <label>Address for service<textarea name="address_for_service" defaultValue={user.address_for_service} /></label>
          {notice && <p className="ok">{notice}</p>}
          {error && <p className="error">{error}</p>}
          <button className="button" type="submit">Save</button>
        </form>
      </section>
    </Shell>
  );
}

export function PrivacyPage() {
  return (
    <Shell>
      <section className="page-pad stack">
        <h1>Privacy</h1>
        <p>
          By the Book stores the landlord’s account, the property address, tenant names and contact details,
          inspection photos, and signatures. A signature also stores the time, the IP address, and the browser,
          so there is a record of who signed.
        </p>
        <p>
          This is personal information under Alberta’s Personal Information Protection Act. Keep the files in Canada.
          The app can store photos on disk for a trial, or in Azure Blob Storage in Canada Central when that account is configured.
        </p>
        <p>
          You can download a tenancy as JSON, including the inspection record, and you can delete a tenancy.
          Deleting removes the photos and signatures with it.
        </p>
        <p>The inspection wording is not legal advice.</p>
      </section>
    </Shell>
  );
}
