import { FormEvent, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from './api';
import { useAuth } from './auth';

export function Shell({ children }: { children: React.ReactNode }) {
  const { user, setUser } = useAuth();
  const navigate = useNavigate();

  async function logout() {
    await api('/api/auth/logout/', { method: 'POST' });
    setUser(null);
    navigate('/');
  }

  return (
    <>
      <header className="top">
        <div className="wrap top-inner">
          <Link className="brand" to={user ? '/home' : '/'}>
            <img src="/icon-192.png" alt="" width="36" height="36" />
            <span>
              By the Book
              <span>Rental records</span>
            </span>
          </Link>
          <nav>
            {user ? (
              <>
                <Link to="/home">Home</Link>
                <Link to="/property">Properties</Link>
                <Link to="/account">Account</Link>
                <button className="text-button" type="button" onClick={() => void logout()}>Sign out</button>
              </>
            ) : (
              <>
                <Link to="/login">Sign in</Link>
                <Link to="/register">Create account</Link>
              </>
            )}
          </nav>
        </div>
      </header>
      <div className="wrap">{children}</div>
      <footer className="site">
        <div className="wrap">
          <p>
            Not legal advice. Deadlines and statements follow published Alberta rules and should be checked
            against the current Act before you rely on them. <Link to="/privacy">Privacy</Link>
          </p>
        </div>
      </footer>
    </>
  );
}

export function Field({
  label, children,
}: { label: string; children: React.ReactNode }) {
  return <label>{label}{children}</label>;
}

export function SignaturePad({ onChange }: { onChange: (blob: Blob | null) => void }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const drawing = useRef(false);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * 2;
    canvas.height = rect.height * 2;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.scale(2, 2);
    ctx.lineWidth = 2;
    ctx.lineCap = 'round';
    ctx.strokeStyle = '#111111';
  }, []);

  function point(event: React.PointerEvent<HTMLCanvasElement>) {
    const canvas = ref.current!;
    const rect = canvas.getBoundingClientRect();
    return { x: event.clientX - rect.left, y: event.clientY - rect.top };
  }

  function start(event: React.PointerEvent<HTMLCanvasElement>) {
    drawing.current = true;
    const ctx = ref.current?.getContext('2d');
    if (!ctx) return;
    const p = point(event);
    ctx.beginPath();
    ctx.moveTo(p.x, p.y);
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function move(event: React.PointerEvent<HTMLCanvasElement>) {
    if (!drawing.current) return;
    const ctx = ref.current?.getContext('2d');
    if (!ctx) return;
    const p = point(event);
    ctx.lineTo(p.x, p.y);
    ctx.stroke();
  }

  function end() {
    drawing.current = false;
    ref.current?.toBlob((blob) => onChange(blob), 'image/png');
  }

  function clear(event: FormEvent) {
    event.preventDefault();
    const canvas = ref.current;
    const ctx = canvas?.getContext('2d');
    if (!canvas || !ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    onChange(null);
  }

  return (
    <div>
      <canvas className="pad" ref={ref} onPointerDown={start} onPointerMove={move} onPointerUp={end} onPointerLeave={end} />
      <button className="text-button" type="button" onClick={clear}>Clear signature</button>
    </div>
  );
}
