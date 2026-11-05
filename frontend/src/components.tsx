import { FormEvent, useEffect, useRef, useState } from 'react';
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom';
import { api } from './api';
import { useAuth } from './auth';

export function Shell({ children }: { children: React.ReactNode }) {
  const { user, setUser } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') setMenuOpen(false);
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  async function logout() {
    await api('/api/auth/logout/', { method: 'POST' });
    setUser(null);
    navigate('/');
  }

  return (
    <>
      <header className="top">
        <div className="top-bar">
          <div className="wrap top-inner">
          <Link className="brand" to={user ? '/home' : '/'}>
            <img src="/icon-192.png" alt="" width="32" height="32" />
            <span className="brand-name">By the Book</span>
            <span className="brand-app">Rental records</span>
          </Link>
          <button
            className="menu-button"
            type="button"
            aria-expanded={menuOpen}
            aria-controls="site-nav"
            onClick={() => setMenuOpen((open) => !open)}
          >
            <span className="menu-icon" />
            <span className="visually-hidden">{menuOpen ? 'Close menu' : 'Open menu'}</span>
          </button>
          <nav id="site-nav" className={menuOpen ? 'is-open' : undefined} onClick={() => setMenuOpen(false)}>
            {user ? (
              user.role === 'tenant' ? (
                <>
                  <NavLink to="/home">Home</NavLink>
                  <NavLink to="/account">Account</NavLink>
                  <button className="text-button" type="button" onClick={() => void logout()}>Sign out</button>
                </>
              ) : (
                <>
                  <NavLink to="/home">Home</NavLink>
                  <NavLink to="/property">Properties</NavLink>
                  <NavLink to="/account">Account</NavLink>
                  <button className="text-button" type="button" onClick={() => void logout()}>Sign out</button>
                </>
              )
            ) : (
              <>
                <NavLink to="/login">Sign in</NavLink>
                <NavLink to="/register">Create account</NavLink>
              </>
            )}
          </nav>
          </div>
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
