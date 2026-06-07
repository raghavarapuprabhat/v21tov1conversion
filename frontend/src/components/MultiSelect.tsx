import { useEffect, useMemo, useRef, useState } from 'react'

// Searchable, scrollable multi-select that scales to ~700-800 options
// (filters by substring, caps rendered rows, virtual-free).
export default function MultiSelect({
  options,
  selected,
  onChange,
  placeholder,
  wide,
}: {
  options: string[]
  selected: string[]
  onChange: (v: string[]) => void
  placeholder: string
  wide?: boolean
}) {
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const h = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', h)
    return () => document.removeEventListener('mousedown', h)
  }, [])

  const filtered = useMemo(
    () => (q ? options.filter((o) => o.toLowerCase().includes(q.toLowerCase())) : options),
    [q, options],
  )
  const CAP = 300
  const shown = filtered.slice(0, CAP)
  const toggle = (v: string) =>
    onChange(selected.includes(v) ? selected.filter((x) => x !== v) : [...selected, v])

  const label =
    selected.length === 0 ? placeholder : selected.length === 1 ? selected[0] : `${selected.length} selected`

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        title={selected.join(', ')}
        className={`flex w-full items-center justify-between gap-1 truncate rounded-md border px-1.5 py-1 text-left text-xs outline-none ${
          selected.length ? 'border-brand-300 bg-brand-50 text-brand-700' : 'border-slate-200 bg-white text-slate-500'
        }`}
      >
        <span className="truncate">{label}</span>
        <span className="text-slate-400">▾</span>
      </button>
      {open && (
        <div className={`absolute z-30 mt-1 rounded-lg border border-slate-200 bg-white p-2 shadow-lg ${wide ? 'w-72' : 'w-52'}`}>
          <input
            autoFocus
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="search…"
            className="mb-1 w-full rounded border border-slate-200 px-2 py-1 text-xs outline-none focus:border-brand-400"
          />
          <div className="flex items-center justify-between px-1 pb-1 text-[10px] text-slate-400">
            <button onClick={() => onChange([])} className="hover:underline">Clear</button>
            <span>{selected.length} sel · {filtered.length} opts</span>
          </div>
          <div className="max-h-56 overflow-auto">
            {shown.map((o) => (
              <label key={o} className="flex items-center gap-2 rounded px-1.5 py-0.5 text-xs hover:bg-slate-50">
                <input type="checkbox" checked={selected.includes(o)} onChange={() => toggle(o)} />
                <span className="truncate" title={o}>{o || '(blank)'}</span>
              </label>
            ))}
            {filtered.length > CAP && (
              <div className="px-1.5 py-1 text-[10px] text-slate-400">+{filtered.length - CAP} more — refine search</div>
            )}
            {filtered.length === 0 && <div className="px-1.5 py-1 text-[10px] text-slate-400">no matches</div>}
          </div>
        </div>
      )}
    </div>
  )
}
