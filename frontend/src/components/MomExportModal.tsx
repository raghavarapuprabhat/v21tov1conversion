import { useState } from 'react'
import { useMomPreview } from '../api/queries'

type Fmt = 'html' | 'md' | 'csv'

const isoLocal = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

function presets() {
  const today = new Date()
  const minus = (n: number) => {
    const d = new Date()
    d.setDate(d.getDate() - n)
    return d
  }
  const monthStart = new Date(today.getFullYear(), today.getMonth(), 1)
  return {
    today: [isoLocal(today), isoLocal(today)] as const,
    week: [isoLocal(minus(6)), isoLocal(today)] as const,
    month: [isoLocal(monthStart), isoLocal(today)] as const,
  }
}

export default function MomExportModal({ onClose }: { onClose: () => void }) {
  const p = presets()
  const [from, setFrom] = useState(p.week[0])
  const [to, setTo] = useState(p.week[1])
  const [fmt, setFmt] = useState<Fmt>('html')

  const valid = !!from && !!to && from <= to
  const preview = useMomPreview(from, to)
  const data = preview.data
  const empty = valid && data && data.events.length === 0

  const downloadUrl = `/api/export/mom?from=${from}&to=${to}&format=${fmt}`

  const Preset = ({ label, range }: { label: string; range: readonly [string, string] }) => {
    const active = from === range[0] && to === range[1]
    return (
      <button
        onClick={() => {
          setFrom(range[0])
          setTo(range[1])
        }}
        className={`rounded-full px-2.5 py-1 text-xs font-medium ring-1 ${
          active ? 'bg-brand-50 text-brand-700 ring-brand-200' : 'bg-white text-slate-500 ring-slate-200 hover:bg-slate-50'
        }`}
      >
        {label}
      </button>
    )
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-slate-900/40 p-4 backdrop-blur-sm">
      <div className="w-full max-w-lg overflow-hidden rounded-2xl bg-white shadow-xl ring-1 ring-slate-200">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">Export Minutes of Meeting</h3>
            <p className="text-xs text-slate-400">Decisions &amp; comments in a date range, grouped by attribute</p>
          </div>
          <button onClick={onClose} className="rounded-md p-1 text-slate-400 hover:bg-slate-100">✕</button>
        </div>

        <div className="space-y-4 p-5">
          {/* date range */}
          <div className="flex flex-wrap items-end gap-3">
            <label className="text-xs font-medium text-slate-500">
              From
              <input
                type="date"
                value={from}
                max={to || undefined}
                onChange={(e) => setFrom(e.target.value)}
                className="mt-1 block rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm outline-none focus:border-brand-500"
              />
            </label>
            <label className="text-xs font-medium text-slate-500">
              To
              <input
                type="date"
                value={to}
                min={from || undefined}
                onChange={(e) => setTo(e.target.value)}
                className="mt-1 block rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm outline-none focus:border-brand-500"
              />
            </label>
            <div className="flex gap-1.5 pb-0.5">
              <Preset label="Today" range={p.today} />
              <Preset label="Last 7 days" range={p.week} />
              <Preset label="This month" range={p.month} />
            </div>
          </div>

          {!valid && (
            <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">
              "From" must be on or before "To".
            </p>
          )}

          {/* preview */}
          {valid && (
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
              {preview.isLoading && <p className="text-xs text-slate-400">Checking activity…</p>}
              {data && (
                <>
                  <div className="flex flex-wrap gap-4 text-sm">
                    <Stat n={data.totals.decisions} label="decisions" />
                    <Stat n={data.totals.comments} label="comments" />
                    <Stat n={data.totals.attributes} label="attributes" />
                    <Stat n={data.totals.participants} label="participants" />
                  </div>
                  {data.participants.length > 0 && (
                    <p className="mt-2 text-xs text-slate-500">By: {data.participants.join(', ')}</p>
                  )}
                  {empty && (
                    <p className="mt-1 text-xs text-amber-600">No changes or comments in this period.</p>
                  )}
                </>
              )}
            </div>
          )}

          {/* format */}
          <div>
            <div className="mb-1 text-xs font-medium text-slate-500">Format</div>
            <div className="flex gap-2">
              {([
                ['html', 'HTML (recommended)'],
                ['md', 'Markdown'],
                ['csv', 'CSV'],
              ] as [Fmt, string][]).map(([v, label]) => (
                <button
                  key={v}
                  onClick={() => setFmt(v)}
                  className={`rounded-lg px-3 py-1.5 text-sm font-medium ring-1 ${
                    fmt === v ? 'bg-brand-600 text-white ring-brand-600' : 'bg-white text-slate-600 ring-slate-300 hover:bg-slate-50'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
            <p className="mt-1.5 text-[11px] text-slate-400">
              HTML is print/email friendly · CSV opens in Excel.
            </p>
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 border-t border-slate-200 px-5 py-3">
          <button onClick={onClose} className="rounded-lg px-3 py-1.5 text-sm text-slate-500 hover:bg-slate-100">
            Close
          </button>
          <a
            href={valid ? downloadUrl : undefined}
            download
            aria-disabled={!valid}
            onClick={(e) => {
              if (!valid) e.preventDefault()
            }}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium text-white ${
              valid ? 'bg-brand-600 hover:bg-brand-700' : 'cursor-not-allowed bg-slate-300'
            }`}
          >
            Download MoM
          </a>
        </div>
      </div>
    </div>
  )
}

function Stat({ n, label }: { n: number; label: string }) {
  return (
    <div className="leading-tight">
      <span className="text-lg font-semibold tabular-nums text-slate-900">{n}</span>{' '}
      <span className="text-xs text-slate-500">{label}</span>
    </div>
  )
}
