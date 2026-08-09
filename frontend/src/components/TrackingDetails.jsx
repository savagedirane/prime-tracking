import { useEffect, useRef } from 'react'
import L from 'leaflet'
import { STATUS_STAGES, statusColor } from '../api'

// Small built-in geocoding dictionary covering common lanes. Extend this as
// new origin/destination cities are added to the system.
const CITY_COORDS = {
  'frankfurt, germany': [50.1109, 8.6821],
  'paris, france': [48.8566, 2.3522],
  'douala, cameroon': [4.0511, 9.7679],
  'yaoundé, cameroon': [3.848, 11.5021],
  'yaounde, cameroon': [3.848, 11.5021],
  'doha, qatar': [25.2854, 51.531],
  'casablanca, morocco': [33.5731, -7.5898],
  'lagos, nigeria': [6.5244, 3.3792],
  'london, uk': [51.5072, -0.1276],
  'dubai, uae': [25.2048, 55.2708],
  'nairobi, kenya': [-1.2921, 36.8219],
}

function geocode(place) {
  if (!place) return null
  const key = place.trim().toLowerCase()
  if (CITY_COORDS[key]) return CITY_COORDS[key]
  // Fuzzy fallback: match on the city name before the comma.
  const city = key.split(',')[0]
  const found = Object.entries(CITY_COORDS).find(([k]) => k.startsWith(city))
  return found ? found[1] : null
}

function RouteMap({ origin, destination, currentLocation }) {
  const mapRef = useRef(null)
  const containerRef = useRef(null)

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return

    const map = L.map(containerRef.current, {
      zoomControl: true,
      attributionControl: true,
    }).setView([15, 20], 2)

    L.tileLayer(
      'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
      {
        attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
        subdomains: 'abcd',
        maxZoom: 19,
      },
    ).addTo(map)

    mapRef.current = map
    return () => {
      map.remove()
      mapRef.current = null
    }
  }, [])

  useEffect(() => {
    const map = mapRef.current
    if (!map) return

    // Clear previous layers before redrawing (keep the tile layer, index 0).
    map.eachLayer((layer) => {
      if (layer instanceof L.TileLayer) return
      map.removeLayer(layer)
    })

    const originCoords = geocode(origin)
    const destCoords = geocode(destination)
    const currentCoords = geocode(currentLocation) || originCoords

    const points = [originCoords, currentCoords, destCoords].filter(Boolean)
    if (points.length === 0) return

    if (originCoords) {
      L.circleMarker(originCoords, {
        radius: 6,
        color: '#64748b',
        fillColor: '#94a3b8',
        fillOpacity: 1,
        weight: 2,
      })
        .bindTooltip(`Origin: ${origin}`)
        .addTo(map)
    }

    if (destCoords) {
      L.circleMarker(destCoords, {
        radius: 6,
        color: '#64748b',
        fillColor: '#334155',
        fillOpacity: 1,
        weight: 2,
      })
        .bindTooltip(`Destination: ${destination}`)
        .addTo(map)
    }

    if (currentCoords) {
      const pulseIcon = L.divIcon({
        className: '',
        html: `<span class="pulse-marker" style="color:#22d3ee;background:#22d3ee;width:12px;height:12px;position:relative;display:block;box-shadow:0 0 8px #22d3ee;"></span>`,
        iconSize: [12, 12],
        iconAnchor: [6, 6],
      })
      L.marker(currentCoords, { icon: pulseIcon })
        .bindTooltip(`Current: ${currentLocation || origin}`)
        .addTo(map)
    }

    if (originCoords && destCoords) {
      L.polyline([originCoords, destCoords], {
        color: '#22d3ee',
        weight: 2,
        opacity: 0.5,
        dashArray: '6 6',
      }).addTo(map)
    }

    if (points.length > 1) {
      map.fitBounds(L.latLngBounds(points), { padding: [40, 40] })
    } else {
      map.setView(points[0], 5)
    }
  }, [origin, destination, currentLocation])

  return <div ref={containerRef} className="h-72 w-full rounded-xl" />
}

function LifecycleProgress({ status }) {
  const currentIndex = STATUS_STAGES.indexOf(status)

  return (
    <div className="flex items-center w-full overflow-x-auto pb-2">
      {STATUS_STAGES.map((stage, i) => {
        const done = i <= currentIndex
        const isLast = i === STATUS_STAGES.length - 1
        return (
          <div key={stage} className="flex items-center flex-1 min-w-[110px]">
            <div className="flex flex-col items-center flex-1">
              <div
                className={`h-3 w-3 rounded-full ring-4 ${
                  done ? 'bg-cyan-400 ring-cyan-400/20' : 'bg-slate-700 ring-slate-800'
                }`}
              />
              <span
                className={`mt-2 text-[11px] text-center leading-tight ${
                  done ? 'text-slate-200' : 'text-slate-500'
                }`}
              >
                {stage}
              </span>
            </div>
            {!isLast && (
              <div
                className={`h-0.5 flex-1 -mt-5 ${i < currentIndex ? 'bg-cyan-400' : 'bg-slate-700'}`}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}

export default function TrackingDetails({ shipment }) {
  const colors = statusColor(shipment.status)
  const latestMilestone = shipment.milestones[shipment.milestones.length - 1]
  const currentLocation = latestMilestone?.location || shipment.origin

  return (
    <div className="space-y-6">
      {/* Header & summary card */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-wider text-slate-500">Waybill</p>
            <h2 className="text-xl font-bold text-white tracking-tight">
              {shipment.tracking_number}
            </h2>
          </div>
          <span
            className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm font-semibold ring-1 ${colors.bg} ${colors.text} ${colors.ring}`}
          >
            <span className={`h-2 w-2 rounded-full ${colors.dot}`} />
            {shipment.status}
          </span>
        </div>

        <div className="mt-6 grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
          <div>
            <p className="text-slate-500">Origin</p>
            <p className="text-slate-200 font-medium">{shipment.origin}</p>
          </div>
          <div>
            <p className="text-slate-500">Destination</p>
            <p className="text-slate-200 font-medium">{shipment.destination}</p>
          </div>
          <div>
            <p className="text-slate-500">Carrier</p>
            <p className="text-slate-200 font-medium">{shipment.carrier}</p>
          </div>
          <div>
            <p className="text-slate-500">Est. Delivery</p>
            <p className="text-slate-200 font-medium">
              {shipment.estimated_delivery
                ? new Date(shipment.estimated_delivery).toLocaleDateString()
                : '—'}
            </p>
          </div>
        </div>

        <div className="mt-8">
          <LifecycleProgress status={shipment.status} />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Route map */}
        <div className="lg:col-span-2 rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
          <p className="text-sm font-semibold text-slate-300 mb-3 px-2">Live Route</p>
          <RouteMap
            origin={shipment.origin}
            destination={shipment.destination}
            currentLocation={currentLocation}
          />
        </div>

        {/* Cargo telemetry sidebar */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
          <p className="text-sm font-semibold text-slate-300">Cargo Manifest</p>
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between">
              <dt className="text-slate-500">Weight</dt>
              <dd className="text-slate-200">{shipment.weight_kg ?? '—'} kg</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500">Dimensions</dt>
              <dd className="text-slate-200">
                {shipment.length_cm && shipment.width_cm && shipment.height_cm
                  ? `${shipment.length_cm}×${shipment.width_cm}×${shipment.height_cm} cm`
                  : '—'}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500">Mode</dt>
              <dd className="text-slate-200">{shipment.shipping_mode}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500">Sender</dt>
              <dd className="text-slate-200">{shipment.sender_name}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500">Recipient</dt>
              <dd className="text-slate-200">{shipment.recipient_name}</dd>
            </div>
          </dl>
        </div>
      </div>

      {/* Milestone audit feed */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
        <p className="text-sm font-semibold text-slate-300 mb-4">Milestone History</p>
        <ol className="space-y-4">
          {[...shipment.milestones].reverse().map((m) => (
            <li key={m.id} className="flex gap-4">
              <div className="flex flex-col items-center">
                <span className="h-2.5 w-2.5 rounded-full bg-cyan-400 mt-1.5" />
                <span className="w-px flex-1 bg-slate-800" />
              </div>
              <div className="pb-2">
                <p className="text-sm font-medium text-slate-200">{m.status}</p>
                <p className="text-xs text-slate-500">
                  {m.location} &middot; {new Date(m.timestamp).toLocaleString()}
                </p>
                {m.note && <p className="text-xs text-slate-400 mt-1">{m.note}</p>}
              </div>
            </li>
          ))}
        </ol>
      </div>
    </div>
  )
}
