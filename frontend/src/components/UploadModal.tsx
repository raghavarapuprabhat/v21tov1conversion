import { useRef, useState } from 'react'
import { useIngestUpload } from '../api/queries'

function FilePick({
  label,
  hint,
  file,
  onPick,
}: {
  label: string
  hint: string
  file: File | null
  onPick: (f: File | null) => void
}) {
  const ref = useRef<HTMLInputElement>(null)
  return (
    <div className="rounded-xl border border-slate-200 p-3">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm font-medium text-slate-800">{label}</div>
          <div className="text-xs text-slate-400">{hint}</div>
        </div>
        <button
          onClick={() => ref.current?.click()}
          className="rounded-lg border border-slate-300 px-2.5 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50"
        >
          Choose…
        </button>
        <input
          ref={ref}
          type="file"
          accept=".xlsx,.xlsm"
          className="hidden"
          onChange={(e) => onPick(e.target.files?.[0] ?? null)}
        />
      </div>
      {file && (
        <div className="mt-2 flex items-center gap-2 text-xs">
          <span className="truncate rounded bg-brand-50 px-2 py-1 font-medium text-brand-700" title={file.name}>
            {file.name}
          </span>
          <button onClick={() => onPick(null)} className="text-slate-400 hover:text-slate-600">remove</button>
        </div>
      )}
    </div>
  )
}

export default function UploadModal({ onClose }: { onClose: () => void }) {
  const [v1, setV1] = useState<File | null>(null)
  const [v2, setV2] = useState<File | null>(null)
  const upload = useIngestUpload()

  const submit = () =>
    upload.mutate(
      { v1, v2 },
      {
        onSuccess: () => {
          // brief pause so the success summary is visible, then close
          setTimeout(onClose, 1200)
        },
      },
    )

  const report = upload.data
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-slate-900/40 p-4 backdrop-blur-sm">
      <div className="w-full max-w-md overflow-hidden rounded-2xl bg-white shadow-xl ring-1 ring-slate-200">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3">
          <h3 className="text-sm font-semibold text-slate-900">Upload workbooks & re-ingest</h3>
          <button onClick={onClose} className="rounded-md p-1 text-slate-400 hover:bg-slate-100">✕</button>
        </div>

        <div className="space-y-3 p-5">
          <p className="text-xs text-slate-500">
            Upload one or both workbooks. Comments &amp; statuses are retained by IS Reference Number.
            Files you skip keep their current version.
          </p>
          <FilePick label="V1 workbook" hint="legacy schema (.xlsx)" file={v1} onPick={setV1} />
          <FilePick label="V2.1 workbook" hint="new schema (.xlsx)" file={v2} onPick={setV2} />

          {upload.isError && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">
              {(upload.error as Error)?.message || 'Upload failed.'}
            </div>
          )}
          {report && (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-700">
              Ingested V1 {report.v1_rows} · V2.1 {report.v2_rows} rows
              {report.reingest?.comments_retained != null &&
                ` · ${report.reingest.comments_retained} comments retained`}
              .
            </div>
          )}
        </div>

        <div className="flex items-center justify-end gap-2 border-t border-slate-200 px-5 py-3">
          <button onClick={onClose} className="rounded-lg px-3 py-1.5 text-sm text-slate-500 hover:bg-slate-100">
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={(!v1 && !v2) || upload.isPending}
            className="rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {upload.isPending ? 'Uploading…' : 'Upload & re-ingest'}
          </button>
        </div>
      </div>
    </div>
  )
}
