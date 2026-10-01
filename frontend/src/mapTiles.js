// Map tile configuration — Leaflet needs NO API key; tile PROVIDERS sometimes
// do. Default: CARTO's dark basemap (keyless). If tiles fail (provider blocks,
// network/firewall), RouteMap automatically falls back down this chain, and
// markers/route lines always render on the dark canvas regardless.
//
// Override any of these in frontend/.env (see .env.example):
//   VITE_MAP_PRESET      carto-dark | carto-light | osm | maptiler | mapbox
//   VITE_MAP_TILE_URL    fully custom URL; may contain {key} and Leaflet {s}/{z}/{x}/{y}{r}
//   VITE_MAP_API_KEY     your provider key (only needed for keyed providers)
//   VITE_MAP_ATTRIBUTION override attribution string for custom URLs
//   VITE_MAP_SUBDOMAINS  for custom URLs using {s} (default "abc")

const TILE_PRESETS = {
  'carto-dark': {
    url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
    subdomains: 'abcd',
    dark: true,
  },
  'carto-light': {
    url: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
    attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
    subdomains: 'abcd',
    dark: false,
  },
  // OpenStreetMap's own tiles — free, keyless, light-themed.
  // Be polite: fine for dev/small apps, heavy traffic needs own provider.
  osm: {
    url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; OpenStreetMap contributors',
    subdomains: 'abc',
    dark: false,
  },
  // Keyed providers — free tiers available, paste your key in VITE_MAP_API_KEY
  // (or just set VITE_MAP_PRESET and the key; URL template is prewired):
  maptiler: {
    url: 'https://api.maptiler.com/maps/dark/{z}/{x}/{y}.png?key={key}',
    attribution: '&copy; OpenStreetMap contributors &copy; MapTiler',
    subdomains: 'abc',
    dark: true,
  },
  mapbox: {
    url: 'https://api.mapbox.com/styles/v1/mapbox/dark-v11/tiles/{z}/{x}/{y}?access_token={key}',
    attribution: '&copy; Mapbox &copy; OpenStreetMap',
    subdomains: 'abc',
    dark: true,
  },
}

export const CANVAS_BG = '#0b1220' // dark canvas behind tiles/markers

export function getTileConfig() {
  const customUrl = import.meta.env.VITE_MAP_TILE_URL
  const key = import.meta.env.VITE_MAP_API_KEY || ''

  if (customUrl) {
    return {
      url: customUrl.replace('{key}', key),
      attribution: import.meta.env.VITE_MAP_ATTRIBUTION || '&copy; OpenStreetMap contributors',
      subdomains: import.meta.env.VITE_MAP_SUBDOMAINS || 'abc',
      dark: true,
    }
  }

  const presetName = import.meta.env.VITE_MAP_PRESET || 'carto-dark'
  const preset = TILE_PRESETS[presetName] || TILE_PRESETS['carto-dark']
  return { ...preset, url: preset.url.replace('{key}', key) }
}

// Fallback chain for automatic failover: whatever the user chose first
// (if valid), then keyless options. Deduped, order preserved.
export function getTileFallbackChain() {
  const chain = [getTileConfig()]
  for (const name of ['carto-dark', 'osm']) {
    const preset = TILE_PRESETS[name]
    const candidate = { ...preset, url: preset.url.replace('{key}', '') }
    if (!chain.some((c) => c.url === candidate.url)) chain.push(candidate)
  }
  return chain
}
