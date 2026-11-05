import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api, Inspection, InspectionItem } from '../api';
import { Shell, SignaturePad } from '../components';

const CONDITIONS = [
  ['good', 'Good'],
  ['fair', 'Fair'],
  ['poor', 'Poor'],
  ['damaged', 'Damaged'],
  ['not_applicable', 'Not applicable'],
];

const draftKey = (id: string) => `bythebook-inspection-${id}`;

export function InspectionPage() {
  const { id } = useParams();
  const [inspection, setInspection] = useState<Inspection | null>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [offline, setOffline] = useState(false);
  const [blobs, setBlobs] = useState<Record<string, Blob | null>>({});

  useEffect(() => {
    if (!id) return;
    api<Inspection>(`/api/inspections/${id}/`)
      .then((loaded) => {
        const cached = localStorage.getItem(draftKey(id));
        if (cached && !loaded.is_locked) {
          const draft = JSON.parse(cached) as Partial<Inspection>;
          const edits = new Map((draft.items || []).map((item) => [item.id, item]));
          setInspection({
            ...loaded,
            ...draft,
            id: loaded.id,
            items: loaded.items.map((item) => ({ ...item, ...(edits.get(item.id) || {}) })),
            signatures: loaded.signatures,
          });
        } else {
          setInspection(loaded);
        }
      })
      .catch((err) => setError(err.message));
  }, [id]);

  useEffect(() => {
    if (!inspection || inspection.is_locked) return;
    localStorage.setItem(draftKey(inspection.id), JSON.stringify({
      conducted_on: inspection.conducted_on,
      presence: inspection.presence,
      landlord_name: inspection.landlord_name,
      tenant_signer_name: inspection.tenant_signer_name,
      disagreement_reasons: inspection.disagreement_reasons,
      occupied_agreement_note: inspection.occupied_agreement_note,
      offered_times: inspection.offered_times,
      general_notes: inspection.general_notes,
      items: inspection.items.map(({ id: itemId, condition, notes }) => ({ id: itemId, condition, notes })),
    }));
  }, [inspection]);

  const rooms = useMemo(() => {
    const groups: { room: string; items: InspectionItem[] }[] = [];
    for (const item of inspection?.items || []) {
      const last = groups[groups.length - 1];
      if (!last || last.room !== item.room) groups.push({ room: item.room, items: [item] });
      else last.items.push(item);
    }
    return groups;
  }, [inspection]);

  function patchLocal(partial: Partial<Inspection>) {
    setInspection((current) => current ? { ...current, ...partial } : current);
  }

  function patchItem(itemId: string, partial: Partial<InspectionItem>) {
    setInspection((current) => {
      if (!current) return current;
      return {
        ...current,
        items: current.items.map((item) => item.id === itemId ? { ...item, ...partial } : item),
      };
    });
  }

  async function save() {
    if (!inspection) return false;
    setError('');
    try {
      const saved = await api<Inspection>(`/api/inspections/${inspection.id}/`, {
        method: 'PATCH',
        body: JSON.stringify({
          conducted_on: inspection.conducted_on || null,
          presence: inspection.presence,
          landlord_name: inspection.landlord_name,
          tenant_signer_name: inspection.tenant_signer_name,
          disagreement_reasons: inspection.disagreement_reasons,
          occupied_agreement_note: inspection.occupied_agreement_note,
          offered_times: inspection.offered_times,
          general_notes: inspection.general_notes,
          items: inspection.items.map((item) => ({ id: item.id, condition: item.condition, notes: item.notes })),
        }),
      });
      setInspection(saved);
      localStorage.removeItem(draftKey(inspection.id));
      setOffline(false);
      setNotice('Saved on the record.');
      return true;
    } catch (err) {
      setOffline(true);
      setError(err instanceof Error ? `${err.message} A copy is still on this phone.` : 'Saved on this phone only.');
      return false;
    }
  }

  async function sign(role: string, name: string) {
    if (!inspection) return;
    const blob = blobs[role];
    if (!blob) {
      setError('Draw the signature before you save it.');
      return;
    }
    const saved = await save();
    if (!saved) return;
    const body = new FormData();
    body.set('role', role);
    body.set('name', name);
    body.set('image', blob, 'signature.png');
    try {
      const saved = await api<Inspection>(`/api/inspections/${inspection.id}/signatures/`, { method: 'POST', body });
      setInspection(saved);
      setNotice('Signature saved.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save the signature.');
    }
  }

  async function finish() {
    if (!inspection) return;
    const savedDraft = await save();
    if (!savedDraft) return;
    try {
      const saved = await api<Inspection>(`/api/inspections/${inspection.id}/finalize/`, { method: 'POST' });
      setInspection(saved);
      setNotice(saved.warning || 'The report is finished and a copy was emailed.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'The report is not ready to finish.');
    }
  }

  async function addPhoto(itemId: string, file: File) {
    if (!inspection) return;
    const body = new FormData();
    body.set('image', file);
    try {
      await api(`/api/inspections/${inspection.id}/items/${itemId}/photos/`, { method: 'POST', body });
      setInspection(await api<Inspection>(`/api/inspections/${inspection.id}/`));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not add the photo.');
    }
  }

  async function revise() {
    if (!inspection) return;
    const revision = await api<Inspection>(`/api/inspections/${inspection.id}/revise/`, { method: 'POST' });
    window.location.assign(`/inspections/${revision.id}`);
  }

  async function handed() {
    if (!inspection) return;
    setInspection(await api<Inspection>(`/api/inspections/${inspection.id}/copy-handed/`, { method: 'POST' }));
    setNotice('Marked as handed to the tenant.');
  }

  if (!inspection) {
    return <Shell><section className="page-pad">{error ? <p className="error">{error}</p> : <p>Loading the inspection…</p>}</section></Shell>;
  }

  const title = inspection.inspection_type === 'move_in' ? 'Move-in inspection' : 'Move-out inspection';
  const locked = inspection.is_locked;

  return (
    <Shell>
      <section className="page-pad stack">
        <p className="muted"><Link to={`/tenancies/${inspection.tenancy}`}>Back to the tenancy</Link> · version {inspection.version}</p>
        <h1>{title}</h1>
        <p className="notice">{inspection.statements.vacant}</p>
        {inspection.inspection_type === 'move_out' && (
          <p className="muted">Move-out rows show the move-in condition beside today’s, so you can see what changed.</p>
        )}
        {offline && <p className="notice">This phone has a draft. Photos still need a connection.</p>}
        {error && <p className="error">{error}</p>}
        {notice && <p className="ok">{notice}</p>}
        {inspection.blockers.length > 0 && !locked && (
          <div className="notice">
            <strong>Still needed before this report counts</strong>
            <ul>{inspection.blockers.map((line) => <li key={line}>{line}</li>)}</ul>
          </div>
        )}

        <div className="card stack">
          <label>Date of the inspection
            <input type="date" disabled={locked} value={inspection.conducted_on || ''} onChange={(e) => patchLocal({ conducted_on: e.target.value })} />
          </label>
          <label>Who was there
            <select disabled={locked} value={inspection.presence} onChange={(e) => patchLocal({ presence: e.target.value as Inspection['presence'] })}>
              <option value="together">Landlord and tenant together</option>
              <option value="refused">Tenant present, refused to sign</option>
              <option value="absent">Tenant absent after two offered times</option>
            </select>
          </label>
          <label>Landlord name on the report
            <input disabled={locked} value={inspection.landlord_name} onChange={(e) => patchLocal({ landlord_name: e.target.value })} />
          </label>
          {inspection.presence !== 'absent' && (
            <label>Tenant or agent name
              <input disabled={locked} value={inspection.tenant_signer_name} onChange={(e) => patchLocal({ tenant_signer_name: e.target.value })} />
            </label>
          )}
          <label>If the premises were occupied, note the agreement
            <textarea disabled={locked} value={inspection.occupied_agreement_note} onChange={(e) => patchLocal({ occupied_agreement_note: e.target.value })} />
          </label>
          {inspection.presence === 'absent' && (
            <OfferedTimes
              locked={locked}
              times={inspection.offered_times}
              onChange={(offered_times) => patchLocal({ offered_times })}
            />
          )}
          {inspection.presence === 'together' && (
            <label>If they disagree, their reasons
              <textarea disabled={locked} value={inspection.disagreement_reasons} onChange={(e) => patchLocal({ disagreement_reasons: e.target.value })} />
            </label>
          )}
          <label>Other notes
            <textarea disabled={locked} value={inspection.general_notes} onChange={(e) => patchLocal({ general_notes: e.target.value })} />
          </label>
        </div>

        {rooms.map((room) => (
          <article className="card" key={room.room}>
            <h2>{room.room}</h2>
            {room.items.map((item) => (
              <div className="item" key={item.id}>
                <h3>{item.item}</h3>
                {item.prior_condition && (
                  <p className="prior">At move-in: {labelFor(item.prior_condition)}{item.prior_notes ? ` — ${item.prior_notes}` : ''}</p>
                )}
                <div className="chips">
                  {CONDITIONS.map(([value, label]) => (
                    <button
                      key={value}
                      type="button"
                      className={item.condition === value ? 'chip on' : 'chip'}
                      disabled={locked}
                      onClick={() => patchItem(item.id, { condition: value })}
                    >{label}</button>
                  ))}
                </div>
                <label>Notes
                  <input disabled={locked} value={item.notes} onChange={(e) => patchItem(item.id, { notes: e.target.value })} />
                </label>
                <div className="row">
                  {item.photos.map((photo) => <img key={photo.id} className="photo" src={photo.url} alt={photo.caption || item.item} />)}
                </div>
                {!locked && (
                  <label>Photo
                    <input type="file" accept="image/*" capture="environment" onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) void addPhoto(item.id, file);
                    }} />
                  </label>
                )}
              </div>
            ))}
          </article>
        ))}

        <article className="card stack">
          <h2>Statements and signatures</h2>
          {(inspection.presence === 'together' || inspection.presence === 'refused') && (
            <Statement
              text={inspection.statements.presence}
              locked={locked}
              role="landlord_presence"
              name={inspection.landlord_name}
              existing={inspection.signatures.find((sig) => sig.role === 'landlord_presence')}
              onBlob={(blob) => setBlobs((current) => ({ ...current, landlord_presence: blob }))}
              onSign={() => void sign('landlord_presence', inspection.landlord_name)}
            />
          )}
          {inspection.presence === 'together' && (
            <>
              <Statement
                text={inspection.statements.agree}
                locked={locked}
                role="tenant_agree"
                name={inspection.tenant_signer_name}
                existing={inspection.signatures.find((sig) => sig.role === 'tenant_agree')}
                onBlob={(blob) => setBlobs((current) => ({ ...current, tenant_agree: blob }))}
                onSign={() => void sign('tenant_agree', inspection.tenant_signer_name)}
              />
              <Statement
                text={`${inspection.statements.disagree} ${inspection.disagreement_reasons}`}
                locked={locked}
                role="tenant_disagree"
                name={inspection.tenant_signer_name}
                existing={inspection.signatures.find((sig) => sig.role === 'tenant_disagree')}
                onBlob={(blob) => setBlobs((current) => ({ ...current, tenant_disagree: blob }))}
                onSign={() => void sign('tenant_disagree', inspection.tenant_signer_name)}
              />
            </>
          )}
          {inspection.presence === 'refused' && (
            <Statement
              text={inspection.statements.refusal}
              locked={locked}
              role="landlord_refusal"
              name={inspection.landlord_name}
              existing={inspection.signatures.find((sig) => sig.role === 'landlord_refusal')}
              onBlob={(blob) => setBlobs((current) => ({ ...current, landlord_refusal: blob }))}
              onSign={() => void sign('landlord_refusal', inspection.landlord_name)}
            />
          )}
          {inspection.presence === 'absent' && (
            <Statement
              text={inspection.statements.absent}
              locked={locked}
              role="landlord_absent"
              name={inspection.landlord_name}
              existing={inspection.signatures.find((sig) => sig.role === 'landlord_absent')}
              onBlob={(blob) => setBlobs((current) => ({ ...current, landlord_absent: blob }))}
              onSign={() => void sign('landlord_absent', inspection.landlord_name)}
            />
          )}
        </article>

        <div className="bar">
          {!locked ? (
            <>
              <button className="button secondary" type="button" onClick={() => void save()}>Save draft</button>
              <button className="button" type="button" onClick={() => void finish()}>Finish report</button>
            </>
          ) : (
            <>
              <a className="button" href={`/api/inspections/${inspection.id}/pdf/`}>Download PDF</a>
              {!inspection.copy_sent_at && <button className="button secondary" type="button" onClick={() => void handed()}>I handed them a copy</button>}
              <button className="button quiet" type="button" onClick={() => void revise()}>Start a revision</button>
            </>
          )}
        </div>
      </section>
    </Shell>
  );
}

function labelFor(code: string) {
  return CONDITIONS.find(([value]) => value === code)?.[1] || 'Not recorded';
}

function OfferedTimes({
  times, onChange, locked,
}: { times: { date: string; time: string }[]; onChange: (times: { date: string; time: string }[]) => void; locked: boolean }) {
  const rows = times.length ? times : [{ date: '', time: '' }, { date: '', time: '' }];
  return (
    <div className="stack">
      <p className="muted">Offer two times, on different days that are not holidays, between 8:00 a.m. and 8:00 p.m.</p>
      {rows.map((row, index) => (
        <div className="grid-2" key={index}>
          <label>Date
            <input type="date" disabled={locked} value={row.date} onChange={(e) => {
              const next = [...rows];
              next[index] = { ...row, date: e.target.value };
              onChange(next);
            }} />
          </label>
          <label>Time
            <input type="time" disabled={locked} value={row.time} onChange={(e) => {
              const next = [...rows];
              next[index] = { ...row, time: e.target.value };
              onChange(next);
            }} />
          </label>
        </div>
      ))}
    </div>
  );
}

function Statement({
  text, role, name, existing, locked, onBlob, onSign,
}: {
  text: string;
  role: string;
  name: string;
  existing?: { url: string; name: string };
  locked: boolean;
  onBlob: (blob: Blob | null) => void;
  onSign: () => void;
}) {
  return (
    <div className="stack">
      <p>{text}</p>
      {existing && <p className="muted">Signed by {existing.name}. <img src={existing.url} alt="" style={{ height: 48 }} /></p>}
      {!locked && (
        <>
          <SignaturePad onChange={onBlob} />
          <button className="button secondary" type="button" onClick={onSign}>Save {name || 'signature'} for this statement</button>
        </>
      )}
      <span hidden>{role}</span>
    </div>
  );
}
