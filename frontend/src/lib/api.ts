const API_BASE = '/api'

function getToken(): string | null {
  return localStorage.getItem('billingpulse_token')
}

export async function api<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken()
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  }
  if (token) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  })

  if (res.status === 401) {
    localStorage.removeItem('billingpulse_token')
    window.location.href = '/login'
    throw new Error('Unauthorized')
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || err.message || 'Request failed')
  }

  if (res.status === 204) return undefined as T
  return res.json()
}

export const auth = {
  login: (email: string, password: string) =>
    api<{ access_token: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  register: (data: {
    email: string
    password: string
    full_name?: string
    practice_name?: string
    practice_npi?: string
  }) =>
    api<{ access_token: string }>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  me: () => api<{ id: number; email: string; full_name: string | null; practice_id: number | null }>('/auth/me'),
}

export const practices = {
  get: () => api<Practice>('/practices/me'),
  create: (data: PracticeInput) =>
    api<Practice>('/practices/me', { method: 'POST', body: JSON.stringify(data) }),
  update: (data: Partial<PracticeInput>) =>
    api<Practice>('/practices/me', { method: 'PUT', body: JSON.stringify(data) }),
}

export const payers = {
  list: () => api<Payer[]>('/payers'),
  create: (data: PayerInput) =>
    api<Payer>('/payers', { method: 'POST', body: JSON.stringify(data) }),
  get: (id: number) => api<Payer>(`/payers/${id}`),
  update: (id: number, data: Partial<PayerInput>) =>
    api<Payer>(`/payers/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (id: number) =>
    api<void>(`/payers/${id}`, { method: 'DELETE' }),
}

export const claims = {
  list: (params?: { status?: string; payer_id?: number; search?: string }) => {
    const sp = new URLSearchParams()
    if (params?.status) sp.set('status', params.status)
    if (params?.payer_id) sp.set('payer_id', String(params.payer_id))
    if (params?.search) sp.set('search', params.search)
    const q = sp.toString()
    return api<Claim[]>(`/claims${q ? `?${q}` : ''}`)
  },
  create: (data: ClaimInput) =>
    api<Claim>('/claims', { method: 'POST', body: JSON.stringify(data) }),
  upload: async (file: File, payerId?: number) => {
    const form = new FormData()
    form.append('file', file)
    const token = getToken()
    const res = await fetch(`${API_BASE}/claims/upload${payerId ? `?payer_id=${payerId}` : ''}`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Upload failed')
    }
    return res.json()
  },
  get: (id: number) => api<Claim>(`/claims/${id}`),
  update: (id: number, data: Partial<ClaimInput>) =>
    api<Claim>(`/claims/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (id: number) =>
    api<void>(`/claims/${id}`, { method: 'DELETE' }),
}

export const metrics = {
  get: (days?: number) =>
    api<Metrics>(`/metrics${days ? `?days=${days}` : ''}`),
}

export interface Metrics {
  total_claims: number
  pending_claims: number
  in_progress_claims: number
  resolved_claims: number
  total_calls: number
  calls_today: number
  calls_this_week: number
  resolution_rate: number
  revenue_recovered: number | null
  calls_by_day: { date: string; count: number }[]
  in_progress_calls: { id: number; claim_id: number; status: string }[]
}

export const calls = {
  initiate: (claimId: number) =>
    api<{ call_id: number; external_id: string }>('/calls/initiate', {
      method: 'POST',
      body: JSON.stringify({ claim_id: claimId }),
    }),
  queue: (claimId: number) =>
    api<{ queued: number; task_ids: string[]; message: string }>('/calls/queue', {
      method: 'POST',
      body: JSON.stringify({ claim_id: claimId }),
    }),
  queueBulk: (claimIds: number[]) =>
    api<{ queued: number; task_ids: string[]; message: string }>('/calls/queue/bulk', {
      method: 'POST',
      body: JSON.stringify({ claim_ids: claimIds }),
    }),
  list: (params?: { claim_id?: number }) => {
    const sp = new URLSearchParams()
    if (params?.claim_id) sp.set('claim_id', String(params.claim_id))
    const q = sp.toString()
    return api<Call[]>(`/calls${q ? `?${q}` : ''}`)
  },
  get: (id: number) => api<Call>(`/calls/${id}`),
}

export interface Call {
  id: number
  claim_id: number
  status: string
  outcome: string | null
  duration_seconds: number | null
  transcript: string | null
  external_id: string | null
  extracted_data?: {
    claim_status?: string
    denial_reason?: string
    denial_code?: string
    action_taken?: string
    next_steps?: string
    summary?: string
  } | null
  created_at?: string
}

export interface Practice {
  id: number
  name: string
  npi: string | null
  tax_id: string | null
  address: string | null
  phone: string | null
}

export interface PracticeInput {
  name: string
  npi?: string
  tax_id?: string
  address?: string
  phone?: string
}

export interface Payer {
  id: number
  practice_id: number
  name: string
  phone: string
  ivr_notes: string | null
  department_code: string | null
}

export interface PayerInput {
  name: string
  phone: string
  ivr_notes?: string
  department_code?: string
}

export interface Claim {
  id: number
  practice_id: number
  payer_id: number
  claim_number: string
  patient_name: string | null
  patient_dob: string | null
  date_of_service: string | null
  amount: number | string | null
  status: string
  denial_reason: string | null
  denial_code: string | null
  notes: string | null
}

export interface ClaimInput {
  payer_id: number
  claim_number: string
  patient_name?: string
  patient_dob?: string
  date_of_service?: string
  amount?: number
  denial_reason?: string
  denial_code?: string
  notes?: string
}
