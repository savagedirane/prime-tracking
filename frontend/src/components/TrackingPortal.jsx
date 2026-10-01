import { useEffect, useRef, useState } from 'react'
import { api, API_BASE } from '../api'
import TrackingDetails from './TrackingDetails'

const POLL_FALLBACK_MS = 30000

export default function TrackingPortal() {
  const [input, setInput] = useState('')
  const [shipment, setShipment] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  // 'live'  = SSE stream connected (instant pushes)
  // 'poll'  = SSE unavailable, polling every 30s
  // 'off'   = nothing tracked yet
  const [liveMode, setLiveMode] = useState('off')

  // Live-update handles for the currently tracked shipment (refs survive
  // re-renders, plain variables would go stale).
  const eventSourceRef = useRef(null)
  const pollTimerRef = useRef(null)

  function stopLiveUpdates() {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current)
      pollTimerRef.current = null
    }
  }

  // Subscribe to the server's SSE stream; instant pushes update the page.
  // If the stream fails (proxy, network, old backend), fall back to polling
  // so customers always eventually see fresh data.
  function subscribeLiveUpdates(trackingNumber) {
    try {
      const es = new EventSource(
        `${API_BASE}/api/v1/shipments/track/${encodeURIComponent(trackingNumber)}/events`
      )
      eventSourceRef.current = es
      es.addEventListener('shipment', (e) => {
        setShipment(JSON.parse(e.data))
        setLiveMode('live')
      })
      es.addEventListener('not_found', () => {
        stopLiveUpdates()
        setLiveMode('off')
        setError('No shipment found for that tracking number')
        setShipment(null)
      })
      es.onerror = () => {
        es.close()
        eventSourceRef.current = null
        startPolling(trackingNumber)
      }
    } catch {
      startPolling(trackingNumber)
    }
  }

  function startPolling(trackingNumber) {
    if (pollTimerRef.current) return
    setLiveMode('poll')
    pollTimerRef.current = setInterval(async () => {
      try {
        setShipment(await api.trackShipment(trackingNumber))
      } catch {
        // shipment removed / network blip — keep showing last known state
      }
    }, POLL_FALLBACK_MS)
  }

  // Leave nothing running when the component unmounts.
  useEffect(() => stopLiveUpdates, [])

  async function handleSubmit(e) {
    e.preventDefault()
    if (!input.trim()) return
    setLoading(true)
    setError(null)
    setShipment(null)
    stopLiveUpdates()
    setLiveMode('off')
    const trackingNumber = input.trim()
    try {
      const data = await api.trackShipment(trackingNumber)
      setShipment(data)
      subscribeLiveUpdates(trackingNumber)
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

      {shipment && <TrackingDetails shipment={shipment} liveMode={liveMode} />}

      {!shipment && !error && (
        <p className="text-center text-slate-600 text-sm">
          Try a sample code: PCL085263034594XYZ or PCL994810238120ABC
        </p>
      )}
    </div>
  )
}
