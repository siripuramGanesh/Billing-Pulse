import type { Call } from '../lib/api'

interface CallDetailModalProps {
  call: Call | null
  onClose: () => void
}

export default function CallDetailModal({ call, onClose }: CallDetailModalProps) {
  if (!call) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={onClose}>
      <div
        className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-center p-4 border-b border-slate-200">
          <h2 className="text-lg font-semibold text-slate-800">Call #{call.id}</h2>
          <button
            onClick={onClose}
            className="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg"
          >
            ✕
          </button>
        </div>
        <div className="p-4 overflow-y-auto flex-1 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs font-medium text-slate-500">Claim ID</p>
              <p className="text-sm text-slate-800">{call.claim_id}</p>
            </div>
            <div>
              <p className="text-xs font-medium text-slate-500">Status</p>
              <span
                className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                  call.status === 'ended' ? 'bg-green-100 text-green-800' : 'bg-blue-100 text-blue-800'
                }`}
              >
                {call.status}
              </span>
            </div>
            <div>
              <p className="text-xs font-medium text-slate-500">Outcome</p>
              <p className="text-sm text-slate-800">{call.outcome || '-'}</p>
            </div>
            <div>
              <p className="text-xs font-medium text-slate-500">Duration</p>
              <p className="text-sm text-slate-800">
                {call.duration_seconds != null ? `${call.duration_seconds}s` : '-'}
              </p>
            </div>
          </div>

          {call.extracted_data?.summary && (
            <div>
              <p className="text-xs font-medium text-slate-500 mb-1">AI Summary</p>
              <p className="text-sm text-slate-800">{call.extracted_data.summary}</p>
            </div>
          )}

          {call.extracted_data?.denial_reason && (
            <div>
              <p className="text-xs font-medium text-slate-500 mb-1">Denial Reason</p>
              <p className="text-sm text-slate-800">{call.extracted_data.denial_reason}</p>
            </div>
          )}

          {call.extracted_data?.next_steps && (
            <div>
              <p className="text-xs font-medium text-slate-500 mb-1">Next Steps</p>
              <p className="text-sm text-slate-800">{call.extracted_data.next_steps}</p>
            </div>
          )}

          {call.transcript && (
            <div>
              <p className="text-xs font-medium text-slate-500 mb-1">Transcript</p>
              <pre className="text-sm text-slate-800 whitespace-pre-wrap bg-slate-50 p-3 rounded-lg max-h-60 overflow-y-auto">
                {call.transcript}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
