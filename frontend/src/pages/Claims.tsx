import { useState, useEffect, useRef } from 'react'
import { claims, payers, calls } from '../lib/api'
import type { Claim as ClaimType, Payer as PayerType } from '../lib/api'

export default function Claims() {
  const [list, setList] = useState<ClaimType[]>([])
  const [payersList, setPayersList] = useState<PayerType[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [payerFilter, setPayerFilter] = useState<number | ''>('')
  const [searchQuery, setSearchQuery] = useState('')
  const [callingClaimId, setCallingClaimId] = useState<number | null>(null)
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [queueing, setQueueing] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const load = () => {
    Promise.all([
      claims.list({
        status: statusFilter || undefined,
        payer_id: payerFilter || undefined,
        search: searchQuery || undefined,
      }),
      payers.list(),
    ])
      .then(([c, p]) => {
        setList(c)
        setPayersList(p)
      })
      .catch(() => setList([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
    const interval = setInterval(load, 8000) // Poll every 8s for real-time status updates
    return () => clearInterval(interval)
  }, [statusFilter, payerFilter, searchQuery])

  const toggleSelect = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleSelectAll = () => {
    const callable = list.filter((c) => c.status !== 'in_progress')
    if (selectedIds.size >= callable.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(callable.map((c) => c.id)))
    }
  }

  const handleCallSelected = async () => {
    const ids = Array.from(selectedIds).filter((id) => {
      const c = list.find((x) => x.id === id)
      return c && c.status !== 'in_progress'
    })
    if (ids.length === 0) return
    setError('')
    setMessage('')
    setQueueing(true)
    try {
      const result = await calls.queueBulk(ids)
      setMessage(result.message)
      setSelectedIds(new Set())
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to queue calls')
    } finally {
      setQueueing(false)
    }
  }

  const handleCall = async (claimId: number) => {
    setError('')
    setMessage('')
    setCallingClaimId(claimId)
    try {
      const result = await calls.initiate(claimId)
      setMessage(`Call initiated for claim. Vapi ID: ${result.external_id}`)
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to initiate call')
    } finally {
      setCallingClaimId(null)
    }
  }

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setError('')
    setMessage('')
    setUploading(true)
    try {
      const result = await claims.upload(file, payerFilter || undefined)
      setMessage(`Uploaded: ${result.created} claims created from ${result.total_rows} rows`)
      if (result.errors?.length) {
        setError(result.errors.slice(0, 5).join('; '))
      }
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  if (loading) return <div>Loading...</div>

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-slate-800">Claims</h1>
        <div className="flex gap-2 items-center">
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.xlsx,.xls"
            onChange={handleUpload}
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading || payersList.length === 0}
            className="px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {uploading ? 'Uploading...' : 'Upload CSV/Excel'}
          </button>
          <button
            onClick={handleCallSelected}
            disabled={queueing || selectedIds.size === 0 || payersList.length === 0}
            className="px-4 py-2 bg-emerald-600 text-white font-medium rounded-lg hover:bg-emerald-700 disabled:opacity-50"
            title="Queue selected claims for background calls"
          >
            {queueing ? 'Queueing...' : `Call selected (${selectedIds.size})`}
          </button>
        </div>
      </div>

      {payersList.length === 0 && (
        <div className="mb-4 p-4 bg-amber-50 text-amber-800 rounded-lg">
          Add at least one payer before uploading claims.
        </div>
      )}

      {error && <div className="mb-4 p-3 rounded-lg bg-red-50 text-red-700 text-sm">{error}</div>}
      {message && <div className="mb-4 p-3 rounded-lg bg-green-50 text-green-700 text-sm">{message}</div>}

      <div className="mb-4 flex flex-wrap gap-4 items-center">
        <input
          type="text"
          placeholder="Search claim # or patient..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="px-3 py-2 border border-slate-300 rounded-lg w-56"
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-2 border border-slate-300 rounded-lg"
        >
          <option value="">All statuses</option>
          <option value="pending">Pending</option>
          <option value="in_progress">In progress</option>
          <option value="resolved">Resolved</option>
          <option value="denied">Denied</option>
          <option value="appeal_required">Appeal required</option>
        </select>
        <select
          value={payerFilter}
          onChange={(e) => setPayerFilter(e.target.value ? Number(e.target.value) : '')}
          className="px-3 py-2 border border-slate-300 rounded-lg"
        >
          <option value="">All payers</option>
          {payersList.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </div>

      <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
        {list.length === 0 ? (
          <div className="p-8 text-center text-slate-500">
            No claims yet. Upload a CSV or Excel file to get started.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-3 text-left">
                    <input
                      type="checkbox"
                      checked={
                      (() => {
                        const callable = list.filter((c) => c.status !== 'in_progress')
                        return callable.length > 0 && callable.every((c) => selectedIds.has(c.id))
                      })()
                    }
                      onChange={toggleSelectAll}
                      className="rounded"
                    />
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-slate-700">Claim #</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-slate-700">Patient</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-slate-700">DOS</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-slate-700">Amount</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-slate-700">Status</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-slate-700">Denial</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-slate-700">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {list.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={selectedIds.has(c.id)}
                        onChange={() => toggleSelect(c.id)}
                        disabled={c.status === 'in_progress'}
                        className="rounded"
                      />
                    </td>
                    <td className="px-4 py-3 text-sm font-medium text-slate-800">{c.claim_number}</td>
                    <td className="px-4 py-3 text-sm text-slate-600">{c.patient_name || '-'}</td>
                    <td className="px-4 py-3 text-sm text-slate-600">{c.date_of_service || '-'}</td>
                    <td className="px-4 py-3 text-sm text-slate-600">
                      {c.amount != null ? `$${Number(c.amount).toFixed(2)}` : '-'}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                          c.status === 'resolved'
                            ? 'bg-green-100 text-green-800'
                            : c.status === 'denied'
                              ? 'bg-red-100 text-red-800'
                              : 'bg-slate-100 text-slate-800'
                        }`}
                      >
                        {c.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-600">{c.denial_reason || '-'}</td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => handleCall(c.id)}
                        disabled={callingClaimId === c.id || c.status === 'in_progress'}
                        className="px-3 py-1 text-sm font-medium text-blue-600 hover:bg-blue-50 rounded disabled:opacity-50"
                        title="Initiate AI call to payer"
                      >
                        {callingClaimId === c.id ? 'Calling...' : 'Call'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
