import { useState, useEffect } from 'react'
import { payers } from '../lib/api'
import type { Payer as PayerType, PayerInput } from '../lib/api'

export default function Payers() {
  const [list, setList] = useState<PayerType[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<PayerType | null>(null)
  const [form, setForm] = useState<PayerInput>({ name: '', phone: '', ivr_notes: '', department_code: '' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const load = () => payers.list().then(setList).finally(() => setLoading(false))

  useEffect(() => {
    load()
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSaving(true)
    try {
      if (editing) {
        await payers.update(editing.id, form)
        setEditing(null)
      } else {
        await payers.create(form)
        setShowForm(false)
      }
      setForm({ name: '', phone: '', ivr_notes: '', department_code: '' })
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this payer?')) return
    try {
      await payers.delete(id)
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed')
    }
  }

  const startEdit = (p: PayerType) => {
    setEditing(p)
    setForm({
      name: p.name,
      phone: p.phone,
      ivr_notes: p.ivr_notes || '',
      department_code: p.department_code || '',
    })
  }

  if (loading) return <div>Loading...</div>

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-slate-800">Payers</h1>
        <button
          onClick={() => {
            setShowForm(true)
            setEditing(null)
            setForm({ name: '', phone: '', ivr_notes: '', department_code: '' })
          }}
          className="px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700"
        >
          Add payer
        </button>
      </div>

      {(showForm || editing) && (
        <form onSubmit={handleSubmit} className="mb-6 p-4 bg-white rounded-lg border border-slate-200 space-y-4">
          {error && <div className="p-2 rounded bg-red-50 text-red-700 text-sm">{error}</div>}
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Name *</label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                required
                className="w-full px-3 py-2 border border-slate-300 rounded-lg"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Phone *</label>
              <input
                type="text"
                value={form.phone}
                onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
                required
                className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                placeholder="1-800-xxx-xxxx"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">IVR notes</label>
            <textarea
              value={form.ivr_notes}
              onChange={(e) => setForm((f) => ({ ...f, ivr_notes: e.target.value }))}
              rows={2}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg"
              placeholder="Press 2 for claims, then 1 for status..."
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Department code</label>
            <input
              type="text"
              value={form.department_code}
              onChange={(e) => setForm((f) => ({ ...f, department_code: e.target.value }))}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg"
              placeholder="e.g. 2"
            />
          </div>
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? 'Saving...' : editing ? 'Update' : 'Add'}
            </button>
            <button
              type="button"
              onClick={() => {
                setShowForm(false)
                setEditing(null)
              }}
              className="px-4 py-2 border border-slate-300 rounded-lg hover:bg-slate-50"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
        {list.length === 0 ? (
          <div className="p-8 text-center text-slate-500">No payers yet. Add one to get started.</div>
        ) : (
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-slate-700">Name</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-slate-700">Phone</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-slate-700">Department</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-slate-700">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {list.map((p) => (
                <tr key={p.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 text-sm text-slate-800">{p.name}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{p.phone}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{p.department_code || '-'}</td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => startEdit(p)}
                      className="text-blue-600 hover:underline text-sm mr-3"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(p.id)}
                      className="text-red-600 hover:underline text-sm"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
