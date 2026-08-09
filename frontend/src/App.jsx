import { useState } from 'react'
import TrackingPortal from './components/TrackingPortal'
import AdminDashboard from './components/AdminDashboard'

export default function App() {
  const [view, setView] = useState('public')

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="h-8 w-8 rounded-lg bg-cyan-400 flex items-center justify-center text-slate-950 font-black">
              P
            </span>
            <span className="font-bold tracking-tight">Prime Crest Logistics</span>
          </div>
          <nav className="flex gap-1 rounded-xl bg-slate-900 p-1 border border-slate-800">
            <button
              onClick={() => setView('public')}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium transition ${
                view === 'public' ? 'bg-cyan-400 text-slate-950' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Live Tracking
            </button>
            <button
              onClick={() => setView('admin')}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium transition ${
                view === 'admin' ? 'bg-cyan-400 text-slate-950' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Admin
            </button>
          </nav>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-10">
        {view === 'public' ? <TrackingPortal /> : <AdminDashboard />}
      </main>
    </div>
  )
}
