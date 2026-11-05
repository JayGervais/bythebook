export type User = {
  id: number;
  email: string;
  full_name: string;
  phone: string;
  address_for_service: string;
};

export type Unit = {
  id: string;
  property: string;
  label: string;
  rooms_template: { room: string; items: string[] }[];
  tasks?: MaintenanceTask[];
};

export type MaintenanceTask = {
  id: string;
  kind: string;
  label: string;
  interval_days: number;
  last_done_on: string | null;
  next_due_on: string;
  note: string;
  unit_label?: string;
  address?: string;
};

export type RentPayment = {
  id: string;
  amount: string;
  paid_on: string;
  method: string;
  method_label: string;
  receipt_number: string;
  note: string;
};

export type NoticeRecord = {
  id: string;
  kind: string;
  served_on: string;
  served_time: string | null;
  effective_on: string;
  effective_time: string | null;
  service_method: string;
  service_label: string;
  reason_code: string;
  reason: string;
  new_rent: string | null;
  body: string;
};

export type TenancyMessage = {
  id: string;
  author_role: string;
  author_name: string;
  body: string;
  created_at: string;
};

export type MaintenanceRequest = {
  id: string;
  description: string;
  status: string;
  requested_by: string;
  requester_name: string;
  resolved_on: string | null;
  created_at: string;
  photos: { id: string; url: string; caption: string }[];
};

export type Property = {
  id: string;
  street_address: string;
  city: string;
  province: string;
  postal_code: string;
  property_type: string;
  units: Unit[];
};

export type Tenant = {
  id: string;
  name: string;
  email: string;
  phone: string;
  invite_expires_at: string | null;
  invite_active: boolean;
};

export type Reminder = {
  id: string;
  kind: string;
  due_on: string;
  headline: string;
  detail: string;
  sent_at: string | null;
  completed_at: string | null;
  tenancy_id?: string;
  address?: string;
  unit?: string;
};

export type InspectionSummary = {
  id: string;
  inspection_type: 'move_in' | 'move_out';
  version: number;
  conducted_on: string | null;
  finalized_at: string | null;
  is_locked: boolean;
  copy_sent_at: string | null;
  presence: string;
};

export type Deposit = {
  id: string;
  amount: string;
  received_on: string;
  trust_deposited_on: string | null;
  statement_sent_on: string | null;
  balance: string;
  damage_allowed: boolean;
  interest_entries: { id: string; covers_year: number; amount: string; paid_on: string; note: string }[];
  deductions: { id: string; kind: string; amount: string; reason: string; created_at: string }[];
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
  notice_of_landlord_on: string | null;
  lease_copy_on: string | null;
  tenants: Tenant[];
  deposit: Deposit | null;
  inspections: InspectionSummary[];
  reminders: Reminder[];
  payments: RentPayment[];
  notices: NoticeRecord[];
  messages: TenancyMessage[];
  maintenance_requests: MaintenanceRequest[];
};

export type InspectionItem = {
  id: string;
  room: string;
  item: string;
  condition: string;
  notes: string;
  sort_order: number;
  prior_condition: string;
  prior_notes: string;
  photos: { id: string; url: string; caption: string; taken_at: string }[];
};

export type Signature = {
  id: string;
  role: string;
  name: string;
  url: string;
  signed_at: string;
};

export type Inspection = {
  id: string;
  tenancy: string;
  inspection_type: 'move_in' | 'move_out';
  version: number;
  conducted_on: string | null;
  presence: 'together' | 'refused' | 'absent';
  landlord_name: string;
  tenant_signer_name: string;
  disagreement_reasons: string;
  occupied_agreement_note: string;
  offered_times: { date: string; time: string }[];
  general_notes: string;
  finalized_at: string | null;
  copy_sent_at: string | null;
  copy_warning: string;
  is_locked: boolean;
  items: InspectionItem[];
  signatures: Signature[];
  statements: Record<string, string>;
  blockers: string[];
  warning?: string;
};

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, body: unknown) {
    super(errorText(body));
    this.status = status;
    this.body = body;
  }
}

export function errorText(body: unknown): string {
  if (!body || typeof body !== 'object') return 'Something went wrong. Try again.';
  const record = body as Record<string, unknown>;
  if (typeof record.detail === 'string') return record.detail;
  if (Array.isArray(record.blockers) && record.blockers.length) {
    return record.blockers.map(String).join(' ');
  }
  const parts: string[] = [];
  for (const [key, value] of Object.entries(record)) {
    if (Array.isArray(value)) parts.push(value.map(String).join(' '));
    else if (typeof value === 'string') parts.push(key === 'non_field_errors' ? value : value);
    else if (value && typeof value === 'object') parts.push(errorText(value));
  }
  return parts.filter(Boolean).join(' ') || 'Something went wrong. Try again.';
}

function readCookie(name: string): string {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : '';
}

async function ensureCsrf(): Promise<string> {
  let token = readCookie('csrftoken');
  if (!token) {
    await fetch('/api/auth/csrf/', { credentials: 'include' });
    token = readCookie('csrftoken');
  }
  return token;
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const method = (options.method || 'GET').toUpperCase();
  const headers = new Headers(options.headers);
  if (method !== 'GET' && method !== 'HEAD') {
    headers.set('X-CSRFToken', await ensureCsrf());
  }
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  const response = await fetch(path, { ...options, headers, credentials: 'include' });
  if (response.status === 204) return undefined as T;
  const text = await response.text();
  const body = text ? JSON.parse(text) : null;
  if (!response.ok) throw new ApiError(response.status, body);
  return body as T;
}

export const money = (value: string | number) =>
  Number(value).toLocaleString('en-CA', { style: 'currency', currency: 'CAD' });

export const prettyDate = (value: string | null) => {
  if (!value) return 'Not set';
  const [year, month, day] = value.slice(0, 10).split('-').map(Number);
  return new Date(year, month - 1, day).toLocaleDateString('en-CA', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
};
