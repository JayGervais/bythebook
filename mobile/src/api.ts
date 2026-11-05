import { readToken } from './storage';

export const API_URL = (process.env.EXPO_PUBLIC_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

export type User = {
  id: number;
  email: string;
  full_name: string;
  phone: string;
  address_for_service: string;
  role?: 'landlord' | 'tenant';
  token?: string;
};

export type Reminder = {
  id: string;
  tenancy_id: string;
  due_on: string;
  headline: string;
  detail: string;
  unit: string;
};

export type MaintenanceTask = {
  id: string;
  label: string;
  next_due_on: string;
  note: string;
  unit_label?: string;
};

export type Tenancy = {
  id: string;
  unit: string;
  unit_label: string;
  address: string;
  start_date: string;
  end_date: string | null;
  rent_amount: string;
  rent_due_day: number;
  period: string;
  status: string;
  tenants: { id: string; name: string; email: string }[];
  payments: { id: string; amount: string; paid_on: string; method_label: string; receipt_number: string; note: string }[];
  notices: { id: string; kind: string; served_on: string; effective_on: string; body: string }[];
  messages: { id: string; author_name: string; body: string }[];
  maintenance_requests: { id: string; description: string; status: string; requester_name: string }[];
  inspections: { id: string; inspection_type: string; version: number; is_locked: boolean; finalized_at: string | null }[];
  deposit: { amount: string; balance: string; received_on: string } | null;
};

export type Property = {
  id: string;
  street_address: string;
  city: string;
  postal_code: string;
  units: { id: string; label: string; tasks?: MaintenanceTask[] }[];
};

export type InspectionItem = {
  id: string;
  room: string;
  item: string;
  condition: string;
  notes: string;
  prior_condition: string;
};

export type Inspection = {
  id: string;
  inspection_type: 'move_in' | 'move_out';
  version: number;
  conducted_on: string | null;
  is_locked: boolean;
  blockers: string[];
  items: InspectionItem[];
};

export class ApiError extends Error {
  constructor(message: string) {
    super(message);
  }
}

function errorText(body: unknown): string {
  if (!body || typeof body !== 'object') return 'Something went wrong. Try again.';
  const record = body as Record<string, unknown>;
  if (typeof record.detail === 'string') return record.detail;
  const parts: string[] = [];
  for (const value of Object.values(record)) {
    if (Array.isArray(value)) parts.push(value.map(String).join(' '));
    else if (typeof value === 'string') parts.push(value);
    else if (value && typeof value === 'object') parts.push(errorText(value));
  }
  return parts.filter(Boolean).join(' ') || 'Something went wrong. Try again.';
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  const token = await readToken();
  if (token) headers.set('Authorization', `Token ${token}`);
  if (options.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, { ...options, headers });
  } catch {
    throw new ApiError(`Cannot reach the API at ${API_URL}.`);
  }
  if (response.status === 204) return undefined as T;
  const text = await response.text();
  const body = text ? JSON.parse(text) : null;
  if (!response.ok) throw new ApiError(errorText(body));
  return body as T;
}

export function money(value: string | number) {
  return Number(value).toLocaleString('en-CA', { style: 'currency', currency: 'CAD' });
}

export function prettyDate(value: string | null) {
  if (!value) return 'Not set';
  const [year, month, day] = value.slice(0, 10).split('-').map(Number);
  return new Date(year, month - 1, day).toLocaleDateString('en-CA', { year: 'numeric', month: 'long', day: 'numeric' });
}
