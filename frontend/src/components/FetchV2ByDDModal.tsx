import { useV2ByDd } from '../api/queries'

const COLUMNS: { key: string; label: string }[] = [
  { key: 'json_path', label: 'Schema + JSON Path' },
  { key: 'clmt_is_ref', label: 'CLMT IS Ref' },
  { key: 'attribute_name', label: 'CCDM Attribute' },
  { key: 'map_entity', label: 'Map Entity' },
  { key: 'map_rp_ind', label: 'Map RP IND' },
  { key: 'map_rp_org', label: 'Map RP ORG' },
  { key: 'data_type_raw', label: 'Data Type' },
  { key: 'mandatory_optional', label: 'Mand/Opt' },
  { key: 'json_attr', label: 'JSON Attr' },
]

export default function FetchV2ByDDModal({ dd, onClose }: { dd: string; onClose: () => void }) {
  const q = useV2ByDd(dd)
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-slate-900/40 p-4 backdrop-blur-sm">
      <div className="max-h-[80vh] w-full max-w-3xl overflow-hidden rounded-2xl bg-white shadow-xl ring-1 ring-slate-200">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3">
          <h3 className="text-sm font-semibold text-slate-900">
            V2.1 records for DD <span className="text-brand-600">{dd}</span>
          </h3>
          <button onClick={onClose} className="rounded-md p-1 text-slate-400 hover:bg-slate-100">✕</button>
        </div>
        <div className="max-h-[65vh] overflow-auto p-2">
          {q.isLoading && <p className="p-4 text-sm text-slate-500">Loading…</p>}
          {q.data && q.data.length === 0 && (
            <p className="p-4 text-sm text-slate-500">No V2.1 record for DD {dd}.</p>
          )}
          {q.data && q.data.length > 0 && (
            <table className="w-full text-left text-xs">
              <thead className="text-slate-500">
                <tr>
                  {COLUMNS.map((c) => (
                    <th key={c.key} className="whitespace-nowrap px-2 py-1 font-medium">{c.label}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {q.data.map((row, i) => (
                  <tr key={i} className="border-t border-slate-100">
                    {COLUMNS.map((c) => (
                      <td key={c.key} className="whitespace-nowrap px-2 py-1.5 text-slate-700">
                        {row[c.key] ?? <span className="text-slate-300">—</span>}
                      </td>
                    ))}
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
