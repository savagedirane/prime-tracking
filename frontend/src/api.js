// Production: set VITE_API_URL to the backend's full URL (e.g. Render).
// Dev/preview: leave unset — same-origin '/api' requests go through the
// Vite dev proxy (vite.config.js) to the local backend, no CORS needed.
const API_BASE = import.meta.env.VITE_API_URL || ''

async function request(path, { method = 'GET', body, token } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  })

  let data = null
  try {
    data = await res.json()
  } catch {
    // no JSON body (e.g. 204 No Content)
  }

  if (!res.ok) {
    const message = data?.detail || `Request failed with status ${res.status}`
    throw new Error(typeof message === 'string' ? message : JSON.stringify(message))
  }

  return data
}

export const api = {
  trackShipment: (trackingNumber) =>
    request(`/api/v1/shipments/track/${encodeURIComponent(trackingNumber)}`),

  adminLogin: (username, password) =>
    request('/api/v1/admin/login', { method: 'POST', body: { username, password } }),

  // Paginated + searchable server-side list
  listShipments: (token, { page = 1, pageSize = 25, status = '', q = '', includeDeleted = false } = {}) => {
    const qs = new URLSearchParams()
    qs.set('page', page)
    qs.set('page_size', pageSize)
    if (status) qs.set('status', status)
    if (q) qs.set('q', q)
    if (includeDeleted) qs.set('include_deleted', 'true')
    return request(`/api/v1/admin/shipments?${qs.toString()}`, { token })
  },

  createShipment: (payload, token) =>
    request('/api/v1/admin/shipments', { method: 'POST', body: payload, token }),

  updateShipment: (trackingNumber, payload, token) =>
    request(`/api/v1/admin/shipments/${encodeURIComponent(trackingNumber)}`, {
      method: 'PATCH',
      body: payload,
      token,
    }),

  deleteShipment: (trackingNumber, token) =>
    request(`/api/v1/admin/shipments/${encodeURIComponent(trackingNumber)}`, {
      method: 'DELETE',
      token,
    }),

  restoreShipment: (trackingNumber, token) =>
    request(`/api/v1/admin/shipments/${encodeURIComponent(trackingNumber)}/restore`, {
      method: 'POST',
      token,
    }),

  addMilestone: (trackingNumber, payload, token) =>
    request(`/api/v1/admin/shipments/${encodeURIComponent(trackingNumber)}/milestones`, {
      method: 'POST',
      body: payload,
      token,
    }),
}

export const STATUS_STAGES = [
  'Order Registered',
  'Departed Origin',
  'In Transit',
  'Customs Clearance',
  'Out for Delivery',
  'Delivered',
]

export function statusColor(status) {
  if (status === 'Delivered') return { text: 'text-emerald-400', bg: 'bg-emerald-400/10', ring: 'ring-emerald-400/30', dot: 'bg-emerald-400' }
  if (status === 'Order Registered') return { text: 'text-amber-400', bg: 'bg-amber-400/10', ring: 'ring-amber-400/30', dot: 'bg-amber-400' }
  return { text: 'text-cyan-400', bg: 'bg-cyan-400/10', ring: 'ring-cyan-400/30', dot: 'bg-cyan-400' }
}
