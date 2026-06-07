import { useEffect, useMemo, useRef, useState } from 'react'

// Searchable, scrollable multi-select that scales to ~700-800 options
// (filters by substring, caps rendered rows, virtual-free). Excel-style
// "(Select All)" tri-state checkbox lets you select everything and then
// deselect a few; when a search is active it acts on the matching options only.
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
  const allRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const h = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', h)
    return () => document.removeEventListener('mousedown', h)
  }, [])

  const selectedSet = useMemo(() => new Set(selected), [selected])
  const filtered = useMemo(
    () => (q ? options.filter((o) => o.toLowerCase().includes(q.toLowerCase())) : options),
    [q, options],
  )
  const CAP = 300
  const shown = filtered.slice(0, CAP)

  const selectedInFiltered = useMemo(
    () => filtered.reduce((n, o) => (selectedSet.has(o) ? n + 1 : n), 0),
    [filtered, selectedSet],
  )
  const allFiltered = filtered.length > 0 && selectedInFiltered === filtered.length
  const someFiltered = selectedInFiltered > 0 && !allFiltered

  // tri-state: indeterminate when only some of the (filtered) options are picked
  useEffect(() => {
    if (allRef.current) allRef.current.indeterminate = someFiltered
  }, [someFiltered, open])

  const toggle = (v: string) =>
    onChange(selected.includes(v) ? selected.filter((x) => x !== v) : [...selected, v])

  const toggleAll = () => {
    if (allFiltered) {
      const drop = new Set(filtered)
      onChange(selected.filter((s) => !drop.has(s)))
    } else {
      onChange(Array.from(new Set([...selected, ...filtered])))
    }
  }

  const label =
    selected.length === 0
      ? placeholder
      : options.length > 0 && selected.length === options.length
        ? 'All'
        : selected.length === 1
          ? selected[0]
          : `${selected.length} selected`

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
          {/* (Select All) — Excel-style, scoped to the current search */}
          <label className="flex items-center gap-2 rounded bg-slate-50 px-1.5 py-1 text-xs font-medium text-slate-600">
            <input ref={allRef} type="checkbox" checked={allFiltered} onChange={toggleAll} />
            <span>{q ? '(Select all matches)' : '(Select All)'}</span>
          </label>
          <div className="flex items-center justify-between px-1 py-1 text-[10px] text-slate-400">
            <button onClick={() => onChange([])} className="hover:underline">Clear all</button>
            <span>{selected.length} sel · {filtered.length} opts</span>
          </div>
          <div className="max-h-56 overflow-auto">
            {shown.map((o) => (
              <label key={o} className="flex items-center gap-2 rounded px-1.5 py-0.5 text-xs hover:bg-slate-50">
                <input type="checkbox" checked={selectedSet.has(o)} onChange={() => toggle(o)} />
                <span className="truncate" title={o}>{o || '(blank)'}</span>
              </label>
            ))}
            {filtered.length > CAP && (
              <div className="px-1.5 py-1 text-[10px] text-slate-400">
                showing {CAP} of {filtered.length} — refine search ((Select All) still applies to all {filtered.length})
              </div>
            )}
            {filtered.length === 0 && <div className="px-1.5 py-1 text-[10px] text-slate-400">no matches</div>}
          </div>
        </div>
      )}
    </div>
  )
}
