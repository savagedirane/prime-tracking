import { useEffect, useState } from 'react'
import { api, STATUS_STAGES, statusColor } from '../api'

const PAGE_SIZE = 10

const emptyShipmentForm = {
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

const emptyEditForm = {
  origin: '',
  destination: '',
  sender_name: '',
  recipient_name: '',
  carrier: '',
  shipping_mode: '',
  weight_kg: '',
  length_cm: '',
  width_cm: '',
  height_cm: '',
  estimated_delivery: '',
}

const inputCls =
  'rounded-xl bg-slate-950 border border-slate-800 px-3 py-2 text-slate-100 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-cyan-400/40'

export default function AdminDashboard() {
  const [token, setToken] = useState(sessionStorage.getItem('pcl_admin_token') || '')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [authed, setAuthed] = useState(false)
  const [authError, setAuthError] = useState(null)
  const [loginBusy, setLoginBusy] = useState(false)

  // Server-side paginated list state
  const [pageData, setPageData] = useState({ items: [], total: 0, page: 1, total_pages: 1 })
  const [page, setPage] = useState(1)
  const [searchInput, setSearchInput] = useState('')
  const [query, setQuery] = useState('') // debounced searchInput
  const [statusFilter, setStatusFilter] = useState('')
  const [showDeleted, setShowDeleted] = useState(false)
  const [loading, setLoading] = useState(false)
  const [reloadKey, setReloadKey] = useState(0)
  const refresh = () => setReloadKey((k) => k + 1)

  const [selected, setSelected] = useState(null)
  const [editing, setEditing] = useState(false)

  const [form, setForm] = useState(emptyShipmentForm)
  const [editForm, setEditForm] = useState(emptyEditForm)
  const [milestoneForm, setMilestoneForm] = useState({ status: 'Departed Origin', location: '', note: '' })
  const [formError, setFormError] = useState(null)
  const [formBusy, setFormBusy] = useState(false)
  const [notice, setNotice] = useState(null)

  // From the JWT (UI affordance only — the server enforces roles for real).
  const role = decodeTokenRole(token)
  const isAdmin = role === 'admin'

  // Debounce the search box so we don't hammer the API on every keystroke.
  useEffect(() => {
    const t = setTimeout(() => setQuery(searchInput), 300)
    return () => clearTimeout(t)
  }, [searchInput])

  useEffect(() => {
    if (!token) return
    let cancelled = false
    setLoading(true)
    api
      .listShipments(token, {
        page,
        pageSize: PAGE_SIZE,
        status: statusFilter,
        q: query,
        includeDeleted: showDeleted,
      })
      .then((res) => {
        if (cancelled) return
        setPageData(res)
        setAuthed(true)
        setAuthError(null)
      })
      .catch((err) => {
        if (cancelled) return
        // Token missing/expired/invalid — drop back to the sign-in screen.
        setAuthed(false)
        setToken('')
        sessionStorage.removeItem('pcl_admin_token')
        setAuthError(err.message)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [token, page, query, statusFilter, showDeleted, reloadKey])

  async function handleLogin(e) {
    e.preventDefault()
    setLoginBusy(true)
    setAuthError(null)
    try {
      const { access_token } = await api.adminLogin(username, password)
      sessionStorage.setItem('pcl_admin_token', access_token)
      setToken(access_token)
      setPassword('')
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
    setPageData({ items: [], total: 0, page: 1, total_pages: 1 })
    setSelected(null)
    setEditing(false)
  }

  async function handleCreate(e) {
    e.preventDefault()
    setFormBusy(true)
    setFormError(null)
    setNotice(null)
    try {
      // No tracking number input — the server generates an unguessable,
      // Luhn-valid number and returns it.
      const payload = {
        ...form,
        weight_kg: form.weight_kg ? Number(form.weight_kg) : null,
        length_cm: form.length_cm ? Number(form.length_cm) : null,
        width_cm: form.width_cm ? Number(form.width_cm) : null,
        height_cm: form.height_cm ? Number(form.height_cm) : null,
      }
      const created = await api.createShipment(payload, token)
      setForm(emptyShipmentForm)
      setNotice(`Shipment created — tracking number ${created.tracking_number}`)
      setPage(1)
      refresh()
    } catch (err) {
      setFormError(err.message)
    } finally {
      setFormBusy(false)
    }
  }

  function startEdit() {
    const s = selected
    setEditForm({
      origin: s.origin || '',
      destination: s.destination || '',
      sender_name: s.sender_name || '',
      recipient_name: s.recipient_name || '',
      carrier: s.carrier || '',
      shipping_mode: s.shipping_mode || '',
      weight_kg: s.weight_kg ?? '',
      length_cm: s.length_cm ?? '',
      width_cm: s.width_cm ?? '',
      height_cm: s.height_cm ?? '',
      estimated_delivery: s.estimated_delivery ? String(s.estimated_delivery).slice(0, 16) : '',
    })
    setFormError(null)
    setEditing(true)
  }

  async function handleSaveEdit(e) {
    e.preventDefault()
    if (!selected) return
    setFormBusy(true)
    setFormError(null)
    try {
      const payload = {
        origin: editForm.origin,
        destination: editForm.destination,
        sender_name: editForm.sender_name,
        recipient_name: editForm.recipient_name,
        carrier: editForm.carrier,
        shipping_mode: editForm.shipping_mode,
        weight_kg: editForm.weight_kg === '' ? null : Number(editForm.weight_kg),
        length_cm: editForm.length_cm === '' ? null : Number(editForm.length_cm),
        width_cm: editForm.width_cm === '' ? null : Number(editForm.width_cm),
        height_cm: editForm.height_cm === '' ? null : Number(editForm.height_cm),
        estimated_delivery: editForm.estimated_delivery
          ? new Date(editForm.estimated_delivery).toISOString()
          : null,
      }
      const updated = await api.updateShipment(selected.tracking_number, payload, token)
      setSelected(updated)
      setEditing(false)
      setNotice(`Shipment ${updated.tracking_number} updated`)
      refresh()
    } catch (err) {
      setFormError(err.message)
    } finally {
      setFormBusy(false)
    }
  }

  async function handleDelete() {
    if (!selected) return
    const tn = selected.tracking_number
    if (!window.confirm(`Delete shipment ${tn}? It will be hidden from tracking but can be restored.`)) return
    setFormBusy(true)
    setFormError(null)
    try {
      await api.deleteShipment(tn, token)
      setSelected({ ...selected, deleted_at: new Date().toISOString() })
      setEditing(false)
      setNotice(`Shipment ${tn} deleted (soft — restorable)`)
      refresh()
    } catch (err) {
      setFormError(err.message)
    } finally {
      setFormBusy(false)
    }
  }

  async function handleRestore() {
    if (!selected) return
    setFormBusy(true)
    setFormError(null)
    try {
      const updated = await api.restoreShipment(selected.tracking_number, token)
      setSelected(updated)
      setNotice(`Shipment ${updated.tracking_number} restored`)
      refresh()
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
      setSelected(updated)
      setMilestoneForm({ status: 'Departed Origin', location: '', note: '' })
      refresh()
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

  const isDeleted = Boolean(selected?.deleted_at)
  const { items, total, total_pages } = pageData

  return (
    <div className="space-y-4">
      {notice && (
        <div className="rounded-xl border border-emerald-400/30 bg-emerald-400/10 px-4 py-3 text-sm text-emerald-300 flex items-center justify-between">
          <span>{notice}</span>
          <button onClick={() => setNotice(null)} className="text-emerald-400/70 hover:text-emerald-300 ml-4">✕</button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Shipment list: search, filter, paginate */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm font-semibold text-slate-300">
              Shipments {loading ? '…' : `(${total})`}
            </p>
            <button
              onClick={handleLogout}
              className="text-xs text-slate-500 hover:text-slate-300 transition"
            >
              Sign out
            </button>
          </div>

          <div className="space-y-2 mb-3">
            <input
              value={searchInput}
              onChange={(e) => {
                setSearchInput(e.target.value)
                setPage(1)
              }}
              placeholder="Search number, name, city…"
              className={`w-full ${inputCls}`}
            />
            <div className="flex items-center gap-2">
              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value)
                  setPage(1)
                }}
                className={`flex-1 ${inputCls}`}
              >
                <option value="">All statuses</option>
                {STATUS_STAGES.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
              <label className="flex items-center gap-1.5 text-xs text-slate-500 cursor-pointer select-none whitespace-nowrap">
                <input
                  type="checkbox"
                  checked={showDeleted}
                  onChange={(e) => {
                    setShowDeleted(e.target.checked)
                    setPage(1)
                  }}
                  className="accent-cyan-400"
                />
                Deleted
              </label>
            </div>
          </div>

          {loading && <p className="text-slate-500 text-sm">Loading…</p>}

          <ul className="space-y-2 max-h-[380px] overflow-y-auto">
            {items.map((s) => {
              const c = statusColor(s.status)
              return (
                <li key={s.id}>
                  <button
                    onClick={() => {
                      setSelected(s)
                      setEditing(false)
                      setFormError(null)
                    }}
                    className={`w-full text-left rounded-xl px-3 py-2 border transition ${
                      selected?.id === s.id
                        ? 'border-cyan-400/50 bg-cyan-400/5'
                        : 'border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <p className="text-sm text-slate-200 font-medium">{s.tracking_number}</p>
                    {s.deleted_at ? (
                      <p className="text-xs mt-0.5 text-red-400">Deleted</p>
                    ) : (
                      <p className={`text-xs mt-0.5 ${c.text}`}>{s.status}</p>
                    )}
                  </button>
                </li>
              )
            })}
            {!loading && items.length === 0 && (
              <li className="text-slate-600 text-sm py-4 text-center">No shipments match.</li>
            )}
          </ul>

          <div className="flex items-center justify-between mt-3 pt-3 border-t border-slate-800">
            <button
              disabled={page <= 1 || loading}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="text-xs px-2 py-1 rounded-lg border border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700 disabled:opacity-40 disabled:hover:border-slate-800 transition"
            >
              ← Prev
            </button>
            <p className="text-xs text-slate-600">
              Page {page} of {Math.max(1, total_pages)}
            </p>
            <button
              disabled={page >= total_pages || loading}
              onClick={() => setPage((p) => p + 1)}
              className="text-xs px-2 py-1 rounded-lg border border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700 disabled:opacity-40 disabled:hover:border-slate-800 transition"
            >
              Next →
            </button>
          </div>
        </div>

        {/* Detail / edit / create */}
        <div className="lg:col-span-2 space-y-6">
          {selected && editing ? (
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
              <p className="text-sm font-semibold text-slate-300 mb-4">
                Edit shipment — {selected.tracking_number}
              </p>
              <form onSubmit={handleSaveEdit} className="grid grid-cols-2 gap-3">
                <input required placeholder="Origin" value={editForm.origin}
                  onChange={(e) => setEditForm({ ...editForm, origin: e.target.value })}
                  className={inputCls} />
                <input required placeholder="Destination" value={editForm.destination}
                  onChange={(e) => setEditForm({ ...editForm, destination: e.target.value })}
                  className={inputCls} />
                <input required placeholder="Sender name" value={editForm.sender_name}
                  onChange={(e) => setEditForm({ ...editForm, sender_name: e.target.value })}
                  className={inputCls} />
                <input required placeholder="Recipient name" value={editForm.recipient_name}
                  onChange={(e) => setEditForm({ ...editForm, recipient_name: e.target.value })}
                  className={inputCls} />
                <input placeholder="Carrier" value={editForm.carrier}
                  onChange={(e) => setEditForm({ ...editForm, carrier: e.target.value })}
                  className={inputCls} />
                <input placeholder="Shipping mode" value={editForm.shipping_mode}
                  onChange={(e) => setEditForm({ ...editForm, shipping_mode: e.target.value })}
                  className={inputCls} />
                <input placeholder="Weight (kg)" value={editForm.weight_kg}
                  onChange={(e) => setEditForm({ ...editForm, weight_kg: e.target.value })}
                  className={inputCls} />
                <label className="flex items-center gap-2 rounded-xl bg-slate-950 border border-slate-800 px-3 text-xs text-slate-500">
                  ETA
                  <input type="datetime-local" value={editForm.estimated_delivery}
                    onChange={(e) => setEditForm({ ...editForm, estimated_delivery: e.target.value })}
                    className="flex-1 bg-transparent text-slate-100 py-2 focus:outline-none" />
                </label>
                <input placeholder="Length (cm)" value={editForm.length_cm}
                  onChange={(e) => setEditForm({ ...editForm, length_cm: e.target.value })}
                  className={inputCls} />
                <input placeholder="Width (cm)" value={editForm.width_cm}
                  onChange={(e) => setEditForm({ ...editForm, width_cm: e.target.value })}
                  className={inputCls} />
                <input placeholder="Height (cm)" value={editForm.height_cm}
                  onChange={(e) => setEditForm({ ...editForm, height_cm: e.target.value })}
                  className={inputCls} />
                <div />
                <div className="col-span-2 flex gap-3">
                  <button type="submit" disabled={formBusy}
                    className="flex-1 rounded-xl bg-cyan-400 text-slate-950 font-semibold px-4 py-2 hover:bg-cyan-300 transition disabled:opacity-50">
                    {formBusy ? 'Saving…' : 'Save changes'}
                  </button>
                  <button type="button" onClick={() => { setEditing(false); setFormError(null) }}
                    className="rounded-xl border border-slate-700 text-slate-400 px-4 py-2 hover:text-slate-200 hover:border-slate-600 transition">
                    Cancel
                  </button>
                </div>
              </form>
              {formError && <p className="text-red-400 text-sm mt-2">{formError}</p>}
            </div>
          ) : selected ? (
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
              <div className="flex items-start justify-between gap-3 mb-1">
                <div>
                  <p className="text-sm font-semibold text-slate-300">
                    {isDeleted ? 'Shipment deleted' : 'Add milestone'} — {selected.tracking_number}
                  </p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {isDeleted ? (
                      <>Hidden from public tracking · history retained</>
                    ) : (
                      <>Current status: {selected.status}</>
                    )}
                  </p>
                </div>
                <div className="flex gap-2 shrink-0">
                  {isDeleted ? (
                    isAdmin && (
                      <button onClick={handleRestore} disabled={formBusy}
                        className="text-xs rounded-lg border border-emerald-400/40 text-emerald-300 px-3 py-1.5 hover:bg-emerald-400/10 transition disabled:opacity-50">
                        Restore
                      </button>
                    )
                  ) : (
                    <>
                      <button onClick={startEdit} disabled={formBusy}
                        className="text-xs rounded-lg border border-slate-700 text-slate-400 px-3 py-1.5 hover:text-slate-200 hover:border-slate-600 transition disabled:opacity-50">
                        Edit
                      </button>
                      {isAdmin && (
                        <button onClick={handleDelete} disabled={formBusy}
                          className="text-xs rounded-lg border border-red-400/30 text-red-400 px-3 py-1.5 hover:bg-red-400/10 transition disabled:opacity-50">
                          Delete
                        </button>
                      )}
                    </>
                  )}
                </div>
              </div>

              {!isDeleted && (
                <form onSubmit={handleAddMilestone} className="grid grid-cols-2 gap-3 mt-4">
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
              )}
              {formError && <p className="text-red-400 text-sm mt-2">{formError}</p>}
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-slate-800 p-6 text-slate-500 text-sm">
              Select a shipment on the left to add a milestone, edit or delete it.
            </div>
          )}

          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
            <p className="text-sm font-semibold text-slate-300 mb-1">Create new shipment</p>
            <p className="text-xs text-slate-600 mb-4">
              A tracking number is generated automatically — no need to invent one.
            </p>
            <form onSubmit={handleCreate} className="grid grid-cols-2 gap-3">
              <input required placeholder="Origin" value={form.origin}
                onChange={(e) => setForm({ ...form, origin: e.target.value })}
                className={inputCls} />
              <input required placeholder="Destination" value={form.destination}
                onChange={(e) => setForm({ ...form, destination: e.target.value })}
                className={inputCls} />
              <input required placeholder="Sender name" value={form.sender_name}
                onChange={(e) => setForm({ ...form, sender_name: e.target.value })}
                className={inputCls} />
              <input required placeholder="Recipient name" value={form.recipient_name}
                onChange={(e) => setForm({ ...form, recipient_name: e.target.value })}
                className={inputCls} />
              <input placeholder="Weight (kg)" value={form.weight_kg}
                onChange={(e) => setForm({ ...form, weight_kg: e.target.value })}
                className={inputCls} />
              <input placeholder="Shipping mode" value={form.shipping_mode}
                onChange={(e) => setForm({ ...form, shipping_mode: e.target.value })}
                className={inputCls} />
              <input placeholder="Length (cm)" value={form.length_cm}
                onChange={(e) => setForm({ ...form, length_cm: e.target.value })}
                className={inputCls} />
              <input placeholder="Width (cm)" value={form.width_cm}
                onChange={(e) => setForm({ ...form, width_cm: e.target.value })}
                className={inputCls} />
              <input placeholder="Height (cm)" value={form.height_cm}
                onChange={(e) => setForm({ ...form, height_cm: e.target.value })}
                className={`col-span-2 ${inputCls}`} />
              <button type="submit" disabled={formBusy}
                className="col-span-2 rounded-xl bg-emerald-400 text-slate-950 font-semibold px-4 py-2 hover:bg-emerald-300 transition disabled:opacity-50">
                {formBusy ? 'Creating…' : 'Create shipment'}
              </button>
            </form>
            {formError && <p className="text-red-400 text-sm mt-2">{formError}</p>}
          </div>
        </div>
      </div>
    </div>
  )
}
