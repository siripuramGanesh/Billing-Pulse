import { useState, useEffect } from 'react'
import { calls } from '../lib/api'
import type { Call as CallType } from '../lib/api'
import CallDetailModal from '../components/CallDetailModal'

export default function Calls() {
  const [list, setList] = useState<CallType[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedCall, setSelectedCall] = useState<CallType | null>(null)

  const load = () => {
    calls
      .list()
      .then(setList)
      .catch(() => setList([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
    const interval = setInterval(load, 5000) // Poll every 5s for real-time updates
    return () => clearInterval(interval)
  }, [])

  if (loading) return <div>Loading...</div>

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-800 mb-6">Call History</h1>

      <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
        {list.length === 0 ? (
          <div className="p-8 text-center text-slate-500">
            No calls yet. Initiate a call from the Claims page.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-slate-700 w-12"></th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-slate-700">Claim ID</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-slate-700">Status</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-slate-700">Outcome</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-slate-700">Duration</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-slate-700">AI Summary</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-slate-700">Transcript</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {list.map((c) => (
                  <tr
                    key={c.id}
                    className="hover:bg-slate-50 cursor-pointer"
                    onClick={() => setSelectedCall(c)}
                  >
                    <td className="px-4 py-3">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          setSelectedCall(c)
                        }}
                        className="text-blue-600 hover:underline text-sm"
                      >
                        View
                      </button>
                    </td>
                    <td className="px-4 py-3 text-sm font-medium text-slate-800">{c.claim_id}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                          c.status === 'ended'
                            ? 'bg-green-100 text-green-800'
                            : c.status === 'in_progress'
                              ? 'bg-blue-100 text-blue-800'
                              : 'bg-slate-100 text-slate-800'
                        }`}
                      >
                        {c.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-600">{c.outcome || '-'}</td>
                    <td className="px-4 py-3 text-sm text-slate-600">
                      {c.duration_seconds != null ? `${c.duration_seconds}s` : '-'}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-600 max-w-xs">
                      {c.extracted_data?.summary || '-'}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-600 max-w-xs truncate">
                      {c.transcript || '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <CallDetailModal call={selectedCall} onClose={() => setSelectedCall(null)} />
    </div>
  )
}
