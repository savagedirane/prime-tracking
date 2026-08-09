const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

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
    // no JSON body (e.g. network error before response)
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

  listShipments: (token) => request('/api/v1/admin/shipments', { token }),

  createShipment: (payload, token) =>
    request('/api/v1/admin/shipments', { method: 'POST', body: payload, token }),

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
