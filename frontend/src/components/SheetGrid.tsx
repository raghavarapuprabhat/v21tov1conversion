import { useMemo, useState } from 'react'
import { apiPostDownload } from '../api/client'
import { useSheet, type V1GapEntry } from '../api/queries'
import MultiSelect from './MultiSelect'

const ROW_KEY = '__row'
const GAP_COL = '__gap'
const PAGE_SIZE = 50

type Edits = Record<string, Record<string, string>>

const colLabel = (c: string) => (c === GAP_COL ? 'Gap' : c)

export default function SheetGrid({
  which,
  editable = false,
  downloadName,
  gapIndex,
  onRowClick,
}: {
  which: 'v1' | 'v2'
  editable?: boolean
  downloadName?: string
  gapIndex?: Record<string, V1GapEntry>
  onRowClick?: (row: number) => void
}) {
  const sheet = useSheet(which)
  const grid = sheet.data

  const [filters, setFilters] = useState<Record<string, string[]>>({})
  const [search, setSearch] = useState('')
  const [hidden, setHidden] = useState<Set<string>>(new Set())
  const [colsOpen, setColsOpen] = useState(false)
  const [page, setPage] = useState(1)
  const [edits, setEdits] = useState<Edits>({})
  const [downloading, setDownloading] = useState(false)

  const columns = grid?.columns ?? []
  const allRows = grid?.rows ?? []
  const displayColumns = useMemo(
    () => (gapIndex ? [GAP_COL, ...columns] : columns),
    [gapIndex, columns],
  )

  const gapEntry = (row: Record<string, string>) => gapIndex?.[String(row[ROW_KEY])]

  const cellVal = (row: Record<string, string>, col: string) => {
    if (col === GAP_COL) return gapEntry(row)?.count ? 'Yes' : 'No'
    const rk = String(row[ROW_KEY])
    return edits[rk]?.[col] ?? row[col] ?? ''
  }

  // distinct values per column (from original data — stable option list)
  const distinct = useMemo(() => {
    const m: Record<string, string[]> = {}
    for (const col of displayColumns) {
      if (col === GAP_COL) {
        m[col] = ['Yes', 'No']
        continue
      }
      const set = new Set<string>()
      for (const r of allRows) set.add(r[col] ?? '')
      m[col] = Array.from(set).sort((a, b) => a.localeCompare(b))
    }
    return m
  }, [displayColumns, allRows])

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    const activeFilters = Object.entries(filters).filter(([, v]) => v.length > 0)
    return allRows.filter((r) => {
      for (const [col, vals] of activeFilters) {
        if (!vals.includes(cellVal(r, col))) return false
      }
      if (q) {
        const hit = columns.some((c) => cellVal(r, c).toLowerCase().includes(q))
        if (!hit) return false
      }
      return true
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [allRows, filters, search, columns, edits])

  const cols = useMemo(() => displayColumns.filter((c) => !hidden.has(c)), [displayColumns, hidden])
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const curPage = Math.min(page, pages)
  const pageRows = filtered.slice((curPage - 1) * PAGE_SIZE, curPage * PAGE_SIZE)

  const activeFilterCount = Object.values(filters).filter((v) => v.length > 0).length
  const editCount = Object.values(edits).reduce((n, m) => n + Object.keys(m).length, 0)

  const setColFilter = (col: string, vals: string[]) => {
    setFilters((f) => ({ ...f, [col]: vals }))
    setPage(1)
  }
  const clearFilters = () => {
    setFilters({})
    setSearch('')
    setPage(1)
  }

  const editCell = (row: Record<string, string>, col: string, value: string) => {
    const rk = String(row[ROW_KEY])
    setEdits((e) => {
      const original = row[col] ?? ''
      const rowEdits = { ...(e[rk] ?? {}) }
      if (value === original) delete rowEdits[col]
      else rowEdits[col] = value
      const next = { ...e }
      if (Object.keys(rowEdits).length === 0) delete next[rk]
      else next[rk] = rowEdits
      return next
    })
  }
  const isEdited = (row: Record<string, string>, col: string) =>
    edits[String(row[ROW_KEY])]?.[col] !== undefined

  const download = async () => {
    if (!grid) return
    setDownloading(true)
    try {
      const rows = allRows.map((r) => {
        const out: Record<string, string> = {}
        for (const c of columns) out[c] = cellVal(r, c)
        return out
      })
      await apiPostDownload(
        '/sheets/v2/download',
        { columns, rows, filename: downloadName ?? 'v2.1_edited.xlsx', sheet: grid.sheet },
        downloadName ?? 'v2.1_edited.xlsx',
      )
    } finally {
      setDownloading(false)
    }
  }

  if (sheet.isLoading) return <p className="text-sm text-slate-400">Loading sheet…</p>
  if (sheet.isError || !grid)
    return (
      <p className="text-sm text-rose-600">
        Could not load the {which.toUpperCase()} workbook. Check that the configured file exists.
      </p>
    )

  return (
    <div className="space-y-3">
      {/* toolbar */}
      <div className="flex flex-wrap items-center gap-2">
        <input
          value={search}
          onChange={(e) => {
            setSearch(e.target.value)
            setPage(1)
          }}
          placeholder="Search all columns…"
          className="w-56 rounded-lg border border-slate-300 px-3 py-1.5 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
        />
        {(activeFilterCount > 0 || search) && (
          <button onClick={clearFilters} className="rounded-lg border border-slate-300 px-2.5 py-1.5 text-xs text-slate-500 hover:bg-slate-50">
            Clear {activeFilterCount > 0 ? `${activeFilterCount} filter${activeFilterCount > 1 ? 's' : ''}` : 'search'}
          </button>
        )}
        <span className="text-xs text-slate-400">
          {filtered.length.toLocaleString()} / {allRows.length.toLocaleString()} rows
        </span>

        <div className="relative ml-auto">
          <button onClick={() => setColsOpen((v) => !v)} className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50">
            Columns ▾
          </button>
          {colsOpen && (
            <div className="absolute right-0 z-20 mt-1 max-h-72 w-56 overflow-auto rounded-lg border border-slate-200 bg-white p-2 shadow-lg">
              {displayColumns.map((c) => (
                <label key={c} className="flex items-center gap-2 rounded px-2 py-1 text-sm hover:bg-slate-50">
                  <input
                    type="checkbox"
                    checked={!hidden.has(c)}
                    onChange={() =>
                      setHidden((h) => {
                        const n = new Set(h)
                        n.has(c) ? n.delete(c) : n.add(c)
                        return n
                      })
                    }
                  />
                  <span className="truncate" title={colLabel(c)}>{colLabel(c)}</span>
                </label>
              ))}
            </div>
          )}
        </div>

        {editable && (
          <>
            {editCount > 0 && (
              <>
                <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700 ring-1 ring-amber-200">
                  {editCount} edit{editCount > 1 ? 's' : ''}
                </span>
                <button onClick={() => setEdits({})} className="rounded-lg border border-slate-300 px-2.5 py-1.5 text-xs text-slate-500 hover:bg-slate-50">
                  Reset edits
                </button>
              </>
            )}
            <button
              onClick={download}
              disabled={downloading}
              className="rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
            >
              {downloading ? 'Preparing…' : 'Download Excel'}
            </button>
          </>
        )}
      </div>

      {/* table */}
      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-500">
            <tr className="border-b border-slate-200">
              <th className="w-10 px-3 py-2 font-medium text-slate-400">#</th>
              {cols.map((c) => (
                <th key={c} className="whitespace-nowrap px-3 py-2 font-medium" title={colLabel(c)}>
                  {colLabel(c)}
                </th>
              ))}
            </tr>
            <tr className="border-b border-slate-200">
              <th className="px-2 py-1.5" />
              {cols.map((c) => (
                <th key={c} className="px-2 py-1.5 font-normal">
                  <MultiSelect
                    options={distinct[c] ?? []}
                    selected={filters[c] ?? []}
                    onChange={(v) => setColFilter(c, v)}
                    placeholder="All"
                  />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pageRows.length === 0 && (
              <tr><td colSpan={cols.length + 1} className="px-3 py-8 text-center text-slate-400">No rows match.</td></tr>
            )}
            {pageRows.map((r) => {
              const entry = gapEntry(r)
              const hasGaps = !!entry?.count
              const clickable = hasGaps && !!onRowClick
              const rowTone = entry?.open
                ? 'bg-amber-50/70 hover:bg-amber-100/70'
                : hasGaps
                  ? 'bg-emerald-50/60 hover:bg-emerald-100/60'
                  : 'hover:bg-brand-50/30'
              return (
                <tr
                  key={r[ROW_KEY]}
                  onClick={clickable ? () => onRowClick!(Number(r[ROW_KEY])) : undefined}
                  className={`border-b border-slate-100 last:border-0 ${rowTone} ${clickable ? 'cursor-pointer' : ''}`}
                >
                  <td className="px-3 py-1.5 text-xs text-slate-300">{r[ROW_KEY]}</td>
                  {cols.map((c) => (
                    <td key={c} className="px-2 py-1 align-top">
                      {c === GAP_COL ? (
                        <GapBadge entry={entry} />
                      ) : editable ? (
                        <input
                          value={cellVal(r, c)}
                          onChange={(e) => editCell(r, c, e.target.value)}
                          className={`w-full min-w-[8rem] rounded border px-1.5 py-1 text-xs outline-none focus:border-brand-400 ${
                            isEdited(r, c) ? 'border-amber-300 bg-amber-50' : 'border-transparent hover:border-slate-200'
                          }`}
                        />
                      ) : (
                        <span className="block max-w-[16rem] truncate text-slate-700" title={cellVal(r, c)}>
                          {cellVal(r, c) || <span className="text-slate-300">—</span>}
                        </span>
                      )}
                    </td>
                  ))}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* pagination */}
      <div className="flex items-center justify-between text-sm text-slate-500">
        <span>{filtered.length.toLocaleString()} rows</span>
        <div className="flex items-center gap-2">
          <button disabled={curPage <= 1} onClick={() => setPage((p) => p - 1)} className="rounded-md border border-slate-300 px-2 py-1 disabled:opacity-40">Prev</button>
          <span>Page {curPage} / {pages}</span>
          <button disabled={curPage >= pages} onClick={() => setPage((p) => p + 1)} className="rounded-md border border-slate-300 px-2 py-1 disabled:opacity-40">Next</button>
        </div>
      </div>
    </div>
  )
}

function GapBadge({ entry }: { entry?: V1GapEntry }) {
  if (!entry?.count)
    return (
      <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-500 ring-1 ring-slate-200">
        No
      </span>
    )
  const tone = entry.open
    ? 'bg-amber-50 text-amber-700 ring-amber-200'
    : 'bg-emerald-50 text-emerald-700 ring-emerald-200'
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ${tone}`}
      title={`${entry.count} gap${entry.count > 1 ? 's' : ''}${entry.open ? `, ${entry.open} open` : ' (all resolved)'} — click row`}
    >
      Yes{entry.count > 1 ? ` (${entry.count})` : ''}
    </span>
  )
}
