import { useEffect, useState } from 'react'
import { api, STATUS_STAGES, statusColor } from '../api'

const emptyShipmentForm = {
  tracking_number: '',
  origin: '',
  destination: '',
  sender_name: '',
  recipient_name: '',
  carrier: 'Prime Crest Logistics',
  shipping_mode: 'Air Express',
  weight_kg: '',
  length_cm: '',
  width_cm: '',
  height_cm: '',
}

export default function AdminDashboard() {
  const [token, setToken] = useState(sessionStorage.getItem('pcl_admin_token') || '')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [authed, setAuthed] = useState(false)
  const [authError, setAuthError] = useState(null)
  const [loginBusy, setLoginBusy] = useState(false)

  const [shipments, setShipments] = useState([])
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState(null)

  const [form, setForm] = useState(emptyShipmentForm)
  const [milestoneForm, setMilestoneForm] = useState({ status: 'Departed Origin', location: '', note: '' })
  const [formError, setFormError] = useState(null)
  const [formBusy, setFormBusy] = useState(false)

  async function loadShipments(activeToken) {
    setLoading(true)
    try {
      const data = await api.listShipments(activeToken)
      setShipments(data)
      setAuthed(true)
      setAuthError(null)
    } catch (err) {
      // Token missing/expired/invalid — drop back to the sign-in screen.
      setAuthed(false)
      setToken('')
      sessionStorage.removeItem('pcl_admin_token')
      setAuthError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (token) loadShipments(token)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function handleLogin(e) {
    e.preventDefault()
    setLoginBusy(true)
    setAuthError(null)
    try {
      const { access_token } = await api.adminLogin(username, password)
      sessionStorage.setItem('pcl_admin_token', access_token)
      setToken(access_token)
      setPassword('')
      await loadShipments(access_token)
    } catch (err) {
      setAuthError(err.message)
    } finally {
      setLoginBusy(false)
    }
  }

  function handleLogout() {
    sessionStorage.removeItem('pcl_admin_token')
    setToken('')
    setAuthed(false)
    setShipments([])
    setSelected(null)
  }

  async function handleCreate(e) {
    e.preventDefault()
    setFormBusy(true)
    setFormError(null)
    try {
      const payload = {
        ...form,
        weight_kg: form.weight_kg ? Number(form.weight_kg) : null,
        length_cm: form.length_cm ? Number(form.length_cm) : null,
        width_cm: form.width_cm ? Number(form.width_cm) : null,
        height_cm: form.height_cm ? Number(form.height_cm) : null,
      }
      const created = await api.createShipment(payload, token)
      setShipments((prev) => [created, ...prev])
      setForm(emptyShipmentForm)
    } catch (err) {
      setFormError(err.message)
    } finally {
      setFormBusy(false)
    }
  }

  async function handleAddMilestone(e) {
    e.preventDefault()
    if (!selected) return
    setFormBusy(true)
    setFormError(null)
    try {
      const updated = await api.addMilestone(selected.tracking_number, milestoneForm, token)
      setShipments((prev) => prev.map((s) => (s.id === updated.id ? updated : s)))
      setSelected(updated)
      setMilestoneForm({ status: 'Departed Origin', location: '', note: '' })
    } catch (err) {
      setFormError(err.message)
    } finally {
      setFormBusy(false)
    }
  }

  if (!authed) {
    return (
      <div className="max-w-sm mx-auto mt-16">
        <h2 className="text-xl font-bold text-white mb-4">Admin sign-in</h2>
        <form onSubmit={handleLogin} className="space-y-3">
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Username"
            autoComplete="username"
            className="w-full rounded-xl bg-slate-900 border border-slate-800 px-4 py-3 text-slate-100 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-cyan-400/50"
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            autoComplete="current-password"
            className="w-full rounded-xl bg-slate-900 border border-slate-800 px-4 py-3 text-slate-100 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-cyan-400/50"
          />
          <button
            type="submit"
            disabled={loginBusy}
            className="w-full rounded-xl bg-cyan-400 text-slate-950 font-semibold px-6 py-3 hover:bg-cyan-300 transition disabled:opacity-50"
          >
            {loginBusy ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
        {authError && <p className="text-red-400 text-sm mt-3">{authError}</p>}
        <p className="text-slate-600 text-xs mt-4">
          Create an admin user first with: python create_admin.py &lt;username&gt; &lt;password&gt;
        </p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Shipment list */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
        <div className="flex items-center justify-between mb-4">
          <p className="text-sm font-semibold text-slate-300">
            Shipments ({shipments.length})
          </p>
          <button
            onClick={handleLogout}
            className="text-xs text-slate-500 hover:text-slate-300 transition"
          >
            Sign out
          </button>
        </div>
        {loading && <p className="text-slate-500 text-sm">Loading…</p>}
        <ul className="space-y-2 max-h-[420px] overflow-y-auto">
          {shipments.map((s) => {
            const c = statusColor(s.status)
            return (
              <li key={s.id}>
                <button
                  onClick={() => setSelected(s)}
                  className={`w-full text-left rounded-xl px-3 py-2 border transition ${
                    selected?.id === s.id
                      ? 'border-cyan-400/50 bg-cyan-400/5'
                      : 'border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <p className="text-sm text-slate-200 font-medium">{s.tracking_number}</p>
                  <p className={`text-xs mt-0.5 ${c.text}`}>{s.status}</p>
                </button>
              </li>
            )
          })}
        </ul>
      </div>

      {/* Create shipment / add milestone */}
      <div className="lg:col-span-2 space-y-6">
        {selected ? (
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
            <p className="text-sm font-semibold text-slate-300 mb-1">
              Add milestone — {selected.tracking_number}
            </p>
            <p className="text-xs text-slate-500 mb-4">
              Current status: {selected.status}
            </p>
            <form onSubmit={handleAddMilestone} className="grid grid-cols-2 gap-3">
              <select
                value={milestoneForm.status}
                onChange={(e) => setMilestoneForm({ ...milestoneForm, status: e.target.value })}
                className="col-span-2 rounded-xl bg-slate-950 border border-slate-800 px-3 py-2 text-slate-100"
              >
                {STATUS_STAGES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
              <input
                required
                placeholder="Location"
                value={milestoneForm.location}
                onChange={(e) => setMilestoneForm({ ...milestoneForm, location: e.target.value })}
                className="col-span-2 rounded-xl bg-slate-950 border border-slate-800 px-3 py-2 text-slate-100 placeholder-slate-600"
              />
              <input
                placeholder="Note (optional)"
                value={milestoneForm.note}
                onChange={(e) => setMilestoneForm({ ...milestoneForm, note: e.target.value })}
                className="col-span-2 rounded-xl bg-slate-950 border border-slate-800 px-3 py-2 text-slate-100 placeholder-slate-600"
              />
              <button
                type="submit"
                disabled={formBusy}
                className="col-span-2 rounded-xl bg-cyan-400 text-slate-950 font-semibold px-4 py-2 hover:bg-cyan-300 transition disabled:opacity-50"
              >
                {formBusy ? 'Saving…' : 'Add milestone'}
              </button>
            </form>
            {formError && <p className="text-red-400 text-sm mt-2">{formError}</p>}
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed border-slate-800 p-6 text-slate-500 text-sm">
            Select a shipment on the left to add a milestone update.
          </div>
        )}

        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
          <p className="text-sm font-semibold text-slate-300 mb-4">Create new shipment</p>
          <form onSubmit={handleCreate} className="grid grid-cols-2 gap-3">
            <input required placeholder="Tracking number" value={form.tracking_number}
              onChange={(e) => setForm({ ...form, tracking_number: e.target.value })}
              className="col-span-2 rounded-xl bg-slate-950 border border-slate-800 px-3 py-2 text-slate-100 placeholder-slate-600" />
            <input required placeholder="Origin" value={form.origin}
              onChange={(e) => setForm({ ...form, origin: e.target.value })}
              className="rounded-xl bg-slate-950 border border-slate-800 px-3 py-2 text-slate-100 placeholder-slate-600" />
            <input required placeholder="Destination" value={form.destination}
              onChange={(e) => setForm({ ...form, destination: e.target.value })}
              className="rounded-xl bg-slate-950 border border-slate-800 px-3 py-2 text-slate-100 placeholder-slate-600" />
            <input required placeholder="Sender name" value={form.sender_name}
              onChange={(e) => setForm({ ...form, sender_name: e.target.value })}
              className="rounded-xl bg-slate-950 border border-slate-800 px-3 py-2 text-slate-100 placeholder-slate-600" />
            <input required placeholder="Recipient name" value={form.recipient_name}
              onChange={(e) => setForm({ ...form, recipient_name: e.target.value })}
              className="rounded-xl bg-slate-950 border border-slate-800 px-3 py-2 text-slate-100 placeholder-slate-600" />
            <input placeholder="Weight (kg)" value={form.weight_kg}
              onChange={(e) => setForm({ ...form, weight_kg: e.target.value })}
              className="rounded-xl bg-slate-950 border border-slate-800 px-3 py-2 text-slate-100 placeholder-slate-600" />
            <input placeholder="Shipping mode" value={form.shipping_mode}
              onChange={(e) => setForm({ ...form, shipping_mode: e.target.value })}
              className="rounded-xl bg-slate-950 border border-slate-800 px-3 py-2 text-slate-100 placeholder-slate-600" />
            <input placeholder="Length (cm)" value={form.length_cm}
              onChange={(e) => setForm({ ...form, length_cm: e.target.value })}
              className="rounded-xl bg-slate-950 border border-slate-800 px-3 py-2 text-slate-100 placeholder-slate-600" />
            <input placeholder="Width (cm)" value={form.width_cm}
              onChange={(e) => setForm({ ...form, width_cm: e.target.value })}
              className="rounded-xl bg-slate-950 border border-slate-800 px-3 py-2 text-slate-100 placeholder-slate-600" />
            <input placeholder="Height (cm)" value={form.height_cm}
              onChange={(e) => setForm({ ...form, height_cm: e.target.value })}
              className="col-span-2 rounded-xl bg-slate-950 border border-slate-800 px-3 py-2 text-slate-100 placeholder-slate-600" />
            <button type="submit" disabled={formBusy}
              className="col-span-2 rounded-xl bg-emerald-400 text-slate-950 font-semibold px-4 py-2 hover:bg-emerald-300 transition disabled:opacity-50">
              {formBusy ? 'Creating…' : 'Create shipment'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
