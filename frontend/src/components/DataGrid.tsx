import { useEffect, useMemo, useRef, useState } from 'react'
import { useBulkStatus, useFacets, useGaps, type GapsParams } from '../api/queries'
import { useDisplayName } from '../state/displayName'
import type { Gap, GapStatus, GapType } from '../types'
import { GAP_CODE } from '../types'
import { ContextChip, GapTypeBadge, SeverityChip, StatusChip } from './chips'

const STATUSES = ['Open', 'Accepted', 'Not applicable']
const SEVERITIES = ['Critical', 'High', 'Medium', 'Low']
const CONTEXTS = ['Entity', 'RP_IND', 'RP_ORG']
const GAP_TYPES: GapType[] = [
  'G1_COVERAGE', 'G2_OCCURRENCE', 'G3_DATATYPE', 'G4_MANDATORY',
  'G5_REVERSE_ORPHAN', 'G6_DD_MISMATCH', 'G7_CARDINALITY', 'G8_DUP_MAPPING', 'G9_DATA_QUALITY',
]

type FilterKind = 'text' | 'select' | 'multi'
interface ColFilter {
  kind: FilterKind
  param: keyof GapsParams
  options?: { value: string; label: string }[]
}
interface Column {
  key: string
  label: string
  hideable: boolean
  filter?: ColFilter
  render: (g: Gap) => React.ReactNode
}

const opts = (xs: string[]) => xs.map((x) => ({ value: x, label: x }))

const COLUMNS: Column[] = [
  { key: 'severity', label: 'Severity', hideable: false, filter: { kind: 'select', param: 'severity', options: opts(SEVERITIES) }, render: (g) => <SeverityChip severity={g.severity} /> },
  { key: 'gap_type', label: 'Type', hideable: true, filter: { kind: 'select', param: 'type', options: GAP_TYPES.map((t) => ({ value: t, label: GAP_CODE[t] })) }, render: (g) => <GapTypeBadge type={g.gap_type} /> },
  { key: 'is_number', label: 'IS', hideable: false, filter: { kind: 'multi', param: 'is_in' }, render: (g) => <span className="font-medium text-slate-800">{g.is_number ?? '—'}</span> },
  { key: 'path', label: 'Path', hideable: true, filter: { kind: 'multi', param: 'path_in' }, render: (g) => <Trunc v={g.v1_path} wide /> },
  { key: 'context', label: 'Context', hideable: true, filter: { kind: 'select', param: 'context', options: opts(CONTEXTS) }, render: (g) => (g.mapping_context ? <ContextChip context={g.mapping_context} /> : <span className="text-slate-300">—</span>) },
  { key: 'v1_value', label: 'V1', hideable: true, filter: { kind: 'text', param: 'v1' }, render: (g) => <Trunc v={g.v1_value} /> },
  { key: 'v2_value', label: 'V2.1', hideable: true, filter: { kind: 'text', param: 'v2' }, render: (g) => <Trunc v={g.v2_value} /> },
  { key: 'detail', label: 'Detail', hideable: true, filter: { kind: 'text', param: 'detail' }, render: (g) => <Trunc v={g.detail} wide /> },
  { key: 'dd_ref', label: 'DD', hideable: true, filter: { kind: 'text', param: 'dd' }, render: (g) => <span className="text-slate-500">{g.dd_ref ?? '—'}</span> },
  { key: 'dd_in_v2', label: 'DD in V2', hideable: true, filter: { kind: 'select', param: 'dd_in_v2', options: [{ value: 'true', label: 'Yes' }, { value: 'false', label: 'No' }] }, render: (g) => <DdInV2 ok={g.dd_in_v2} /> },
  { key: 'status', label: 'Status', hideable: false, filter: { kind: 'select', param: 'status', options: opts(STATUSES) }, render: (g) => <StatusChip status={g.status} /> },
]

const PAGE_SIZE = 25

export default function DataGrid({
  type,
  onOpen,
  autoOpen,
}: {
  type?: string
  onOpen: (g: Gap) => void
  autoOpen?: string
}) {
  const { name } = useDisplayName()
  const facets = useFacets(type)
  const [search, setSearch] = useState('')
  const [filters, setFilters] = useState<Record<string, string>>({})
  const [debounced, setDebounced] = useState<Record<string, string>>({})
  const [isSel, setIsSel] = useState<string[]>([])
  const [pathSel, setPathSel] = useState<string[]>([])
  const [sort, setSort] = useState('severity')
  const [page, setPage] = useState(1)
  const [hidden, setHidden] = useState<Set<string>>(new Set())
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [colsOpen, setColsOpen] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => setDebounced(filters), 250)
    return () => clearTimeout(t)
  }, [filters])
  useEffect(() => setPage(1), [debounced, search, isSel, pathSel])

  const active = useMemo(() => {
    const a: Record<string, string> = {}
    Object.entries(debounced).forEach(([k, v]) => {
      if (v) a[k] = v
    })
    return a
  }, [debounced])

  const params: GapsParams = {
    ...active,
    type: type ?? active.type,
    is_in: isSel.length ? isSel : undefined,
    path_in: pathSel.length ? pathSel : undefined,
    search: search || undefined,
    sort,
    page,
    page_size: PAGE_SIZE,
  }
  const gaps = useGaps(params)
  const bulk = useBulkStatus()

  const cols = useMemo(() => COLUMNS.filter((c) => !hidden.has(c.key)), [hidden])
  const rows = gaps.data?.rows ?? []
  const total = gaps.data?.total ?? 0
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  const autoOpened = useRef(false)
  useEffect(() => {
    if (autoOpen && !autoOpened.current && rows.length > 0) {
      const row = autoOpen === '1' ? rows[0] : rows.find((r) => r.gap_id === autoOpen)
      if (row) {
        autoOpened.current = true
        onOpen(row)
      }
    }
  }, [autoOpen, rows, onOpen])

  const setFilter = (param: string, value: string) => setFilters((f) => ({ ...f, [param]: value }))
  const activeFilterCount =
    Object.keys(active).length + (isSel.length ? 1 : 0) + (pathSel.length ? 1 : 0)
  const clearFilters = () => {
    setFilters({})
    setIsSel([])
    setPathSel([])
  }

  const toggleSort = (key: string) =>
    setSort((s) => (s === key ? `-${key}` : s === `-${key}` ? key : key))
  const toggleSel = (id: string) =>
    setSelected((s) => {
      const n = new Set(s)
      n.has(id) ? n.delete(id) : n.add(id)
      return n
    })
  const allOnPage = rows.length > 0 && rows.every((r) => selected.has(r.gap_id))
  const toggleAll = () =>
    setSelected((s) => {
      const n = new Set(s)
      if (allOnPage) rows.forEach((r) => n.delete(r.gap_id))
      else rows.forEach((r) => n.add(r.gap_id))
      return n
    })

  const exportUrl = () => {
    const u = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => {
      if (k === 'page' || k === 'page_size') return
      if (Array.isArray(v)) v.forEach((item) => u.append(k, String(item)))
      else if (v) u.append(k, String(v))
    })
    return `/api/export?${u.toString()}`
  }
  const applyBulk = (st: GapStatus) =>
    bulk.mutate({ gapIds: [...selected], status: st, author: name || 'anon' }, { onSuccess: () => setSelected(new Set()) })

  const renderFilter = (c: Column) => {
    if (c.key === 'is_number')
      return <MultiSelect options={facets.data?.is_numbers ?? []} selected={isSel} onChange={setIsSel} placeholder="All IS" />
    if (c.key === 'path')
      return <MultiSelect options={facets.data?.paths ?? []} selected={pathSel} onChange={setPathSel} placeholder="All paths" wide />
    if (!c.filter || (c.key === 'gap_type' && type)) return <span className="block h-7" />
    if (c.filter.kind === 'select')
      return (
        <select
          value={filters[c.filter.param as string] ?? ''}
          onChange={(e) => setFilter(c.filter!.param as string, e.target.value)}
          className="w-full rounded-md border border-slate-200 bg-white px-1.5 py-1 text-xs text-slate-600 outline-none focus:border-brand-400"
        >
          <option value="">All</option>
          {c.filter.options?.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      )
    return (
      <input
        value={filters[c.filter.param as string] ?? ''}
        onChange={(e) => setFilter(c.filter!.param as string, e.target.value)}
        placeholder="filter…"
        className="w-full rounded-md border border-slate-200 px-1.5 py-1 text-xs outline-none placeholder:text-slate-300 focus:border-brand-400"
      />
    )
  }

  return (
    <div className="space-y-3">
      {/* toolbar */}
      <div className="flex flex-wrap items-center gap-2">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search all…"
          className="w-56 rounded-lg border border-slate-300 px-3 py-1.5 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
        />
        {activeFilterCount > 0 && (
          <button onClick={clearFilters} className="rounded-lg border border-slate-300 px-2.5 py-1.5 text-xs text-slate-500 hover:bg-slate-50">
            Clear {activeFilterCount} filter{activeFilterCount > 1 ? 's' : ''}
          </button>
        )}
        <div className="relative ml-auto">
          <button onClick={() => setColsOpen((v) => !v)} className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50">
            Columns ▾
          </button>
          {colsOpen && (
            <div className="absolute right-0 z-20 mt-1 w-44 rounded-lg border border-slate-200 bg-white p-2 shadow-lg">
              {COLUMNS.filter((c) => c.hideable).map((c) => (
                <label key={c.key} className="flex items-center gap-2 rounded px-2 py-1 text-sm hover:bg-slate-50">
                  <input
                    type="checkbox"
                    checked={!hidden.has(c.key)}
                    onChange={() =>
                      setHidden((h) => {
                        const n = new Set(h)
                        n.has(c.key) ? n.delete(c.key) : n.add(c.key)
                        return n
                      })
                    }
                  />
                  {c.label}
                </label>
              ))}
            </div>
          )}
        </div>
        <a href={exportUrl()} className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50">Export CSV</a>
      </div>

      {/* bulk bar */}
      {selected.size > 0 && (
        <div className="flex items-center gap-2 rounded-lg border border-brand-200 bg-brand-50 px-3 py-2 text-sm">
          <span className="font-medium text-brand-700">{selected.size} selected</span>
          <span className="text-slate-400">— set status:</span>
          {STATUSES.map((s) => (
            <button key={s} onClick={() => applyBulk(s as GapStatus)} className="rounded-md bg-white px-2 py-0.5 text-xs font-medium text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50">{s}</button>
          ))}
          <button onClick={() => setSelected(new Set())} className="ml-auto text-xs text-slate-500 hover:underline">Clear</button>
        </div>
      )}

      {/* table */}
      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-500">
            <tr className="border-b border-slate-200">
              <th className="w-8 px-3 py-2"><input type="checkbox" checked={allOnPage} onChange={toggleAll} /></th>
              {cols.map((c) => (
                <th key={c.key} onClick={() => toggleSort(c.key)} className="cursor-pointer whitespace-nowrap px-3 py-2 font-medium hover:text-slate-800">
                  {c.label}
                  {sort === c.key && ' ▲'}
                  {sort === `-${c.key}` && ' ▼'}
                </th>
              ))}
            </tr>
            <tr className="border-b border-slate-200">
              <th className="px-2 py-1.5" />
              {cols.map((c) => (
                <th key={c.key} className="px-2 py-1.5 font-normal">{renderFilter(c)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {gaps.isLoading && (
              <tr><td colSpan={cols.length + 1} className="px-3 py-8 text-center text-slate-400">Loading…</td></tr>
            )}
            {!gaps.isLoading && rows.length === 0 && (
              <tr><td colSpan={cols.length + 1} className="px-3 py-8 text-center text-slate-400">No gaps match.</td></tr>
            )}
            {rows.map((g) => (
              <tr key={g.gap_id} onClick={() => onOpen(g)} className="cursor-pointer border-b border-slate-100 last:border-0 hover:bg-brand-50/40">
                <td className="px-3 py-2" onClick={(e) => e.stopPropagation()}>
                  <input type="checkbox" checked={selected.has(g.gap_id)} onChange={() => toggleSel(g.gap_id)} />
                </td>
                {cols.map((c) => (
                  <td key={c.key} className="px-3 py-2 align-top">{c.render(g)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* pagination */}
      <div className="flex items-center justify-between text-sm text-slate-500">
        <span>{total} gaps</span>
        <div className="flex items-center gap-2">
          <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)} className="rounded-md border border-slate-300 px-2 py-1 disabled:opacity-40">Prev</button>
          <span>Page {page} / {pages}</span>
          <button disabled={page >= pages} onClick={() => setPage((p) => p + 1)} className="rounded-md border border-slate-300 px-2 py-1 disabled:opacity-40">Next</button>
        </div>
      </div>
    </div>
  )
}

// Searchable, scrollable multi-select that scales to ~700-800 options
// (filters by substring, caps rendered rows, virtual-free).
function MultiSelect({
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

  const label = selected.length === 0 ? placeholder : selected.length === 1 ? selected[0] : `${selected.length} selected`

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
                <span className="truncate" title={o}>{o}</span>
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

function DdInV2({ ok }: { ok: boolean }) {
  return ok ? (
    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700 ring-1 ring-emerald-200" title="DD number is present in V2.1">
      ✓ Yes
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-500 ring-1 ring-slate-200" title="DD number not found in V2.1">
      – No
    </span>
  )
}

function Trunc({ v, wide }: { v?: string | null; wide?: boolean }) {
  if (!v) return <span className="text-slate-300">—</span>
  return (
    <span className={`block truncate text-slate-700 ${wide ? 'max-w-[14rem]' : 'max-w-[10rem]'}`} title={v}>
      {v}
    </span>
  )
}
