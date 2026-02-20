import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { practices, metrics } from '../lib/api'
import type { Metrics as MetricsType } from '../lib/api'

export default function Dashboard() {
  const [practice, setPractice] = useState<{ name: string } | null>(null)
  const [metricsData, setMetricsData] = useState<MetricsType | null>(null)
  const [loading, setLoading] = useState(true)

  const load = () => {
    Promise.all([
      practices.get().catch(() => null),
      metrics.get(7).catch(() => null),
    ]).then(([p, m]) => {
      setPractice(p)
      setMetricsData(m)
    }).finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
    const interval = setInterval(load, 10000) // Poll every 10s
    return () => clearInterval(interval)
  }, [])

  if (loading) return <div>Loading...</div>

  const m = metricsData

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-800 mb-6">Dashboard</h1>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-8">
        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <h3 className="text-sm font-medium text-slate-500">Practice</h3>
          <p className="mt-1 text-xl font-semibold text-slate-800">
            {practice?.name || 'Not set up'}
          </p>
          <Link to="/practice" className="mt-2 text-sm text-blue-600 hover:underline">
            {practice ? 'Edit' : 'Set up'} practice
          </Link>
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <h3 className="text-sm font-medium text-slate-500">Total Claims</h3>
          <p className="mt-1 text-xl font-semibold text-slate-800">{m?.total_claims ?? 0}</p>
          <p className="mt-1 text-xs text-slate-500">
            {m?.pending_claims ?? 0} pending · {m?.in_progress_claims ?? 0} in progress · {m?.resolved_claims ?? 0} resolved
          </p>
          <Link to="/claims" className="mt-2 text-sm text-blue-600 hover:underline">
            View claims
          </Link>
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <h3 className="text-sm font-medium text-slate-500">Calls</h3>
          <p className="mt-1 text-xl font-semibold text-slate-800">{m?.total_calls ?? 0}</p>
          <p className="mt-1 text-xs text-slate-500">
            {m?.calls_today ?? 0} today · {m?.calls_this_week ?? 0} this week
          </p>
          <Link to="/calls" className="mt-2 text-sm text-blue-600 hover:underline">
            View call history
          </Link>
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <h3 className="text-sm font-medium text-slate-500">Resolution Rate</h3>
          <p className="mt-1 text-xl font-semibold text-slate-800">{m?.resolution_rate ?? 0}%</p>
          <p className="mt-1 text-xs text-slate-500">of ended calls resolved</p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2 mb-8">
        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <h2 className="text-lg font-semibold text-slate-800 mb-4">Revenue Recovered</h2>
          <p className="text-3xl font-bold text-emerald-600">
            ${(m?.revenue_recovered ?? 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </p>
          <p className="mt-1 text-sm text-slate-500">From resolved claims</p>
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <h2 className="text-lg font-semibold text-slate-800 mb-4">Calls This Week</h2>
          {m?.calls_by_day && m.calls_by_day.length > 0 ? (
            <div className="flex items-end gap-1 h-24">
              {m.calls_by_day.map((d) => (
                <div
                  key={d.date}
                  className="flex-1 flex flex-col items-center gap-1"
                  title={`${d.date}: ${d.count} calls`}
                >
                  <div
                    className="w-full bg-blue-500 rounded-t min-h-[4px]"
                    style={{
                      height: `${Math.max(4, (d.count / Math.max(...m.calls_by_day.map((x) => x.count), 1)) * 80)}px`,
                    }}
                  />
                  <span className="text-xs text-slate-500 truncate max-w-full">
                    {new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-slate-500">No calls yet</p>
          )}
        </div>
      </div>

      {m?.in_progress_calls && m.in_progress_calls.length > 0 && (
        <div className="bg-white rounded-lg border border-slate-200 p-6 mb-8">
          <h2 className="text-lg font-semibold text-slate-800 mb-4">In Progress</h2>
          <div className="space-y-2">
            {m.in_progress_calls.map((c) => (
              <div
                key={c.id}
                className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0"
              >
                <span className="text-sm text-slate-600">Call #{c.id} (Claim #{c.claim_id})</span>
                <span className="inline-flex px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800">
                  {c.status}
                </span>
              </div>
            ))}
          </div>
          <Link to="/calls" className="mt-4 text-sm text-blue-600 hover:underline">
            View all calls
          </Link>
        </div>
      )}

      <div className="bg-white rounded-lg border border-slate-200 p-6">
        <h2 className="text-lg font-semibold text-slate-800 mb-4">Getting started</h2>
        <ol className="list-decimal list-inside space-y-2 text-slate-600">
          <li>Set up your practice (name, NPI, billing info)</li>
          <li>Add payers (insurance companies with phone numbers)</li>
          <li>Upload claims via CSV or Excel</li>
          <li>Initiate calls or queue multiple claims for background processing</li>
        </ol>
      </div>
    </div>
  )
}
