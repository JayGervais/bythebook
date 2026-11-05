import { createContext, useContext, useEffect, useState } from 'react';
import { api, User } from './api';
import { readToken, writeToken } from './storage';

type AuthValue = {
  user: User | null;
  ready: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  register: (form: Record<string, string>) => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    readToken()
      .then((token) => (token ? api<User>('/api/auth/me/') : null))
      .then((me) => setUser(me))
      .catch(() => writeToken(null))
      .finally(() => setReady(true));
  }, []);

  async function signIn(email: string, password: string) {
    const me = await api<User>('/api/auth/login/', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    await writeToken(me.token || null);
    setUser(me);
  }

  async function register(form: Record<string, string>) {
    const me = await api<User>('/api/auth/register/', {
      method: 'POST',
      body: JSON.stringify(form),
    });
    await writeToken(me.token || null);
    setUser(me);
  }

  async function signOut() {
    try {
      await api('/api/auth/logout/', { method: 'POST' });
    } catch {
      // The token is cleared locally either way.
    }
    await writeToken(null);
    setUser(null);
  }

  return <AuthContext.Provider value={{ user, ready, signIn, register, signOut }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error('AuthProvider is missing.');
  return value;
}
