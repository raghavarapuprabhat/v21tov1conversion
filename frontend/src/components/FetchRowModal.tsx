import { useSheetRow } from '../api/queries'

const ROW_KEY = '__row'

// Shows a single uploaded-workbook row (all original columns, as is) for a gap's
// V1 or V2.1 source row. Fired by the "Fetch entire V1/V2.1 row" buttons.
export default function FetchRowModal({
  which,
  row,
  onClose,
}: {
  which: 'v1' | 'v2'
  row: number
  onClose: () => void
}) {
  const q = useSheetRow(which, row)
  const label = which === 'v1' ? 'V1' : 'V2.1'
  const data = q.data
  const cols = data ? data.columns.filter((c) => c !== ROW_KEY) : []

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-slate-900/40 p-4 backdrop-blur-sm">
      <div className="max-h-[80vh] w-full max-w-2xl overflow-hidden rounded-2xl bg-white shadow-xl ring-1 ring-slate-200">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3">
          <h3 className="text-sm font-semibold text-slate-900">
            Entire <span className="text-brand-600">{label}</span> row
            <span className="ml-2 font-normal text-slate-400">
              {data ? `${data.sheet} · row ${row}` : `row ${row}`}
            </span>
          </h3>
          <button onClick={onClose} className="rounded-md p-1 text-slate-400 hover:bg-slate-100">✕</button>
        </div>
        <div className="max-h-[68vh] overflow-auto p-2">
          {q.isLoading && <p className="p-4 text-sm text-slate-500">Loading…</p>}
          {q.isError && <p className="p-4 text-sm text-rose-600">Could not load {label} row {row}.</p>}
          {data && (
            <table className="w-full text-left text-sm">
              <tbody>
                {cols.map((c) => (
                  <tr key={c} className="border-b border-slate-100 last:border-0">
                    <th className="w-2/5 whitespace-nowrap px-3 py-1.5 align-top font-medium text-slate-500">
                      {c}
                    </th>
                    <td className="px-3 py-1.5 align-top text-slate-800">
                      {data.row[c] ? (
                        <span className="break-words">{data.row[c]}</span>
                      ) : (
                        <span className="text-slate-300">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}
