import { useState } from 'react'
import { useGaps } from '../api/queries'
import type { Gap } from '../types'
import { ContextChip, GapTypeBadge, StatusChip } from './chips'
import ConversationPanel from './ConversationPanel'

// Side panel for a clicked V1 sheet row: lists the gap(s) anchored to that row.
// Picking one opens the full conversation panel (status update + comments).
export default function RowGapsPanel({ row, onClose }: { row: number; onClose: () => void }) {
  const gaps = useGaps({ v1_row: row, page_size: 200, sort: 'gap_type' })
  const rows = gaps.data?.rows ?? []
  const [active, setActive] = useState<Gap | null>(null)

  if (active) return <ConversationPanel gap={active} onClose={() => setActive(null)} />

  return (
    <aside className="fixed inset-y-0 right-0 z-40 flex w-full max-w-md flex-col border-l border-slate-200 bg-white shadow-2xl">
      <header className="flex items-start justify-between border-b border-slate-200 p-4">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">V1 sheet · row {row}</h3>
          <p className="mt-0.5 text-xs text-slate-400">
            {gaps.isLoading ? 'Loading…' : `${rows.length} gap${rows.length === 1 ? '' : 's'} on this row · click to review`}
          </p>
        </div>
        <button onClick={onClose} className="rounded-md p-1 text-slate-400 hover:bg-slate-100">✕</button>
      </header>

      <div className="flex-1 space-y-2 overflow-auto p-4">
        {!gaps.isLoading && rows.length === 0 && (
          <p className="text-sm text-slate-400">No gaps recorded for this row.</p>
        )}
        {rows.map((g) => (
          <button
            key={g.gap_id}
            onClick={() => setActive(g)}
            className="block w-full rounded-xl border border-slate-200 p-3 text-left transition hover:border-brand-200 hover:bg-brand-50/40"
          >
            <div className="flex flex-wrap items-center gap-1.5">
              <GapTypeBadge type={g.gap_type} />
              {g.mapping_context && <ContextChip context={g.mapping_context} />}
              <span className="ml-auto"><StatusChip status={g.status} /></span>
            </div>
            <p className="mt-1.5 text-sm text-slate-700">{g.detail}</p>
            {(g.v1_value || g.v2_value) && (
              <p className="mt-1 text-xs text-slate-400">
                V1: <span className="text-slate-600">{g.v1_value ?? '—'}</span>
                {'  ·  '}V2.1: <span className="text-slate-600">{g.v2_value ?? '—'}</span>
              </p>
            )}
          </button>
        ))}
      </div>
    </aside>
  )
}
