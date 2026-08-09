import { useState } from 'react'
import { api } from '../api'
import TrackingDetails from './TrackingDetails'

export default function TrackingPortal() {
  const [input, setInput] = useState('')
  const [shipment, setShipment] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!input.trim()) return
    setLoading(true)
    setError(null)
    setShipment(null)
    try {
      const data = await api.trackShipment(input.trim())
      setShipment(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-extrabold text-white tracking-tight">
          Track your shipment
        </h1>
        <p className="text-slate-400 mt-2">
          Enter your waybill number to see live status and location.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="flex gap-3 mb-10">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="e.g. PCL085263034594XYZ"
          className="flex-1 rounded-xl bg-slate-900 border border-slate-800 px-4 py-3 text-slate-100 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-cyan-400/50"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-xl bg-cyan-400 text-slate-950 font-semibold px-6 py-3 hover:bg-cyan-300 transition disabled:opacity-50"
        >
          {loading ? 'Searching…' : 'Track'}
        </button>
      </form>

      {error && (
        <div className="rounded-xl border border-red-900 bg-red-950/40 text-red-300 px-4 py-3 mb-6">
          {error}
        </div>
      )}

      {shipment && <TrackingDetails shipment={shipment} />}

      {!shipment && !error && (
        <p className="text-center text-slate-600 text-sm">
          Try a sample code: PCL085263034594XYZ or PCL994810238120ABC
        </p>
      )}
    </div>
  )
}
