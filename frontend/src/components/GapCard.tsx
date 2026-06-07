import type { GapSummary } from '../types'
import { GAP_CODE, GAP_LABELS } from '../types'

export default function GapCard({ s, onClick }: { s: GapSummary; onClick: () => void }) {
  const open = s.by_status['Open'] ?? 0
  return (
    <button
      onClick={onClick}
      className="group flex w-full flex-col rounded-2xl border border-slate-200 bg-white p-5 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-brand-200 hover:shadow-md"
    >
      <div className="flex items-center justify-between">
        <span className="rounded-md bg-brand-50 px-2 py-0.5 text-xs font-bold text-brand-700">
          {GAP_CODE[s.gap_type]}
        </span>
        <span className="text-3xl font-semibold tabular-nums text-slate-900">{s.total}</span>
      </div>
      <h3 className="mt-2 text-sm font-semibold text-slate-900">{GAP_LABELS[s.gap_type]}</h3>

      {s.metrics ? (
        <div className="mt-3 grid grid-cols-3 gap-2 text-center">
          <Funnel label="missing" value={s.metrics.total_missing} tone="text-slate-900" />
          <Funnel label="not-null" value={s.metrics.nullable_false} tone="text-orange-600" />
          <Funnel label="root min=1" value={s.metrics.parent_min1} tone="text-rose-600" />
        </div>
      ) : (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {Object.entries(s.by_status).map(([k, v]) => (
            <span key={k} className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] text-slate-600">
              {k}: {v}
            </span>
          ))}
        </div>
      )}

      <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3 text-xs text-slate-500">
        <span>{open} open</span>
        <span className="text-brand-600 group-hover:underline">View table →</span>
      </div>
    </button>
  )
}

function Funnel({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div className="rounded-lg bg-slate-50 py-2">
      <div className={`text-xl font-semibold tabular-nums ${tone}`}>{value}</div>
      <div className="text-[10px] uppercase tracking-wide text-slate-400">{label}</div>
    </div>
  )
}
