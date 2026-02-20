import { useState, useEffect } from 'react'
import { practices } from '../lib/api'
import type { Practice as PracticeType, PracticeInput } from '../lib/api'

export default function Practice() {
  const [practice, setPractice] = useState<PracticeType | null>(null)
  const [form, setForm] = useState<PracticeInput>({
    name: '',
    npi: '',
    tax_id: '',
    address: '',
    phone: '',
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  useEffect(() => {
    practices
      .get()
      .then((p) => {
        setPractice(p)
        setForm({
          name: p.name,
          npi: p.npi || '',
          tax_id: p.tax_id || '',
          address: p.address || '',
          phone: p.phone || '',
        })
      })
      .catch(() => setPractice(null))
      .finally(() => setLoading(false))
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setMessage('')
    setSaving(true)
    try {
      if (practice) {
        await practices.update(form)
        setMessage('Practice updated successfully')
      } else {
        await practices.create(form)
        setMessage('Practice created successfully')
        const p = await practices.get()
        setPractice(p)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div>Loading...</div>

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-800 mb-6">Practice</h1>

      <form onSubmit={handleSubmit} className="max-w-xl space-y-4">
        {error && (
          <div className="p-3 rounded-lg bg-red-50 text-red-700 text-sm">{error}</div>
        )}
        {message && (
          <div className="p-3 rounded-lg bg-green-50 text-green-700 text-sm">{message}</div>
        )}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Practice name *</label>
          <input
            type="text"
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            required
            className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">NPI</label>
          <input
            type="text"
            value={form.npi}
            onChange={(e) => setForm((f) => ({ ...f, npi: e.target.value }))}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            placeholder="1234567890"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Tax ID</label>
          <input
            type="text"
            value={form.tax_id}
            onChange={(e) => setForm((f) => ({ ...f, tax_id: e.target.value }))}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Address</label>
          <textarea
            value={form.address}
            onChange={(e) => setForm((f) => ({ ...f, address: e.target.value }))}
            rows={2}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Phone</label>
          <input
            type="text"
            value={form.phone}
            onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <button
          type="submit"
          disabled={saving}
          className="px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {saving ? 'Saving...' : practice ? 'Update' : 'Create'} practice
        </button>
      </form>
    </div>
  )
}
