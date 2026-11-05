import { FormEvent, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api, Inspection } from '../api';
import { SignaturePad } from '../components';

type InvitePayload = {
  tenant_name: string;
  address: string;
  unit: string;
  inspections: Inspection[];
  messages: { id: string; author_name: string; body: string }[];
  requests: { id: string; description: string; status: string }[];
};

export function InvitePage() {
  const { token } = useParams();
  const [payload, setPayload] = useState<InvitePayload | null>(null);
  const [error, setError] = useState('');
  const [choice, setChoice] = useState<'agree' | 'disagree'>('agree');
  const [reasons, setReasons] = useState('');
  const [name, setName] = useState('');
  const [blob, setBlob] = useState<Blob | null>(null);
  const [done, setDone] = useState('');
  const [note, setNote] = useState('');
  const [request, setRequest] = useState('');

  useEffect(() => {
    api<InvitePayload>(`/api/invite/${token}/`)
      .then((data) => {
        setPayload(data);
        setName(data.tenant_name);
      })
      .catch((err) => setError(err.message));
  }, [token]);

  const open = payload?.inspections.find((inspection) => !inspection.is_locked && inspection.presence === 'together')
    || payload?.inspections.find((inspection) => !inspection.is_locked);

  async function sign() {
    if (!open || !token) return;
    if (!blob) {
      setError('Draw your signature first.');
      return;
    }
    const body = new FormData();
    body.set('inspection_id', open.id);
    body.set('choice', choice);
    body.set('reasons', reasons);
    body.set('name', name);
    body.set('image', blob, 'signature.png');
    try {
      const result = await api<{ finalized: boolean }>(`/api/invite/${token}/sign/`, { method: 'POST', body });
      setDone(result.finalized
        ? 'Thank you. The report is finished. You can download the PDF below.'
        : 'Your signature is saved. The landlord still has a few things to complete.');
      setPayload(await api<InvitePayload>(`/api/invite/${token}/`));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save the signature.');
    }
  }

  async function sendNote(event: FormEvent) {
    event.preventDefault();
    if (!token) return;
    try {
      await api(`/api/invite/${token}/messages/`, { method: 'POST', body: JSON.stringify({ body: note }) });
      setNote('');
      setPayload(await api<InvitePayload>(`/api/invite/${token}/`));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not send that note.');
    }
  }

  async function sendRequest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    const body = new FormData(event.currentTarget);
    body.set('description', request);
    try {
      await api(`/api/invite/${token}/requests/`, { method: 'POST', body });
      setRequest('');
      setPayload(await api<InvitePayload>(`/api/invite/${token}/`));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not send that request.');
    }
  }

  return (
    <div className="wrap page-pad stack">
      <p className="brand">By the Book</p>
      <h1>Inspection report</h1>
      {error && <p className="error">{error}</p>}
      {!payload && !error && <p>Loading…</p>}
      {payload && (
        <>
          <p>{payload.unit} at {payload.address}</p>
          <p className="notice">This report records the condition of the premises. It is not legal advice. Agree with the report, or disagree and state the reasons.</p>
          {done && <p className="ok">{done}</p>}
          {payload.inspections.map((inspection) => (
            <article className="card stack" key={inspection.id}>
              <h2>{inspection.inspection_type === 'move_in' ? 'Move-in' : 'Move-out'} · version {inspection.version}</h2>
              <p>{inspection.statements.vacant}</p>
              <ul>
                {inspection.items.map((item) => (
                  <li key={item.id}>
                    <strong>{item.room} — {item.item}:</strong> {item.condition || 'not filled in'}
                    {item.prior_condition ? ` (move-in was ${item.prior_condition})` : ''}
                    {item.notes ? ` — ${item.notes}` : ''}
                  </li>
                ))}
              </ul>
              <a href={`/api/invite/${token}/inspections/${inspection.id}/pdf/`}>Download PDF</a>
            </article>
          ))}
          <article className="card stack">
            <h2>Messages</h2>
            <ul>{payload.messages.map((row) => <li key={row.id}><strong>{row.author_name}:</strong> {row.body}</li>)}</ul>
            <form className="stack" onSubmit={sendNote}>
              <label>Note to the landlord<textarea required value={note} onChange={(e) => setNote(e.target.value)} /></label>
              <button className="button secondary" type="submit">Send</button>
            </form>
          </article>
          <article className="card stack">
            <h2>Maintenance</h2>
            <ul>{payload.requests.map((row) => <li key={row.id}>{row.description} · {row.status.replace(/_/g, ' ')}</li>)}</ul>
            <form className="stack" onSubmit={sendRequest}>
              <label>What needs attention?<textarea required value={request} onChange={(e) => setRequest(e.target.value)} /></label>
              <label>Photo<input type="file" name="image" accept="image/*" /></label>
              <button className="button secondary" type="submit">Send request</button>
            </form>
          </article>
          {open && !open.is_locked && open.presence === 'together' && (
            <article className="card stack">
              <h2>Your signature</h2>
              <label>Your name<input value={name} onChange={(e) => setName(e.target.value)} /></label>
              <div className="chips">
                <button type="button" className={choice === 'agree' ? 'chip on' : 'chip'} onClick={() => setChoice('agree')}>I agree</button>
                <button type="button" className={choice === 'disagree' ? 'chip on' : 'chip'} onClick={() => setChoice('disagree')}>I disagree</button>
              </div>
              {choice === 'disagree' && (
                <label>What do you disagree with?<textarea value={reasons} onChange={(e) => setReasons(e.target.value)} /></label>
              )}
              <p>{choice === 'agree' ? open.statements.agree : open.statements.disagree}</p>
              <SignaturePad onChange={setBlob} />
              <button className="button" type="button" onClick={() => void sign()}>Sign the report</button>
            </article>
          )}
        </>
      )}
    </div>
  );
}
