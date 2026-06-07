import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSummary } from '../api/queries'
import GapCard from '../components/GapCard'
import UploadModal from '../components/UploadModal'

export default function LandingPage() {
  const summary = useSummary()
  const navigate = useNavigate()
  const [uploadOpen, setUploadOpen] = useState(false)

  const total = summary.data?.reduce((a, s) => a + s.total, 0) ?? 0

  return (
    <section className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Gap Analysis</h1>
          <p className="mt-1 text-sm text-slate-500">
            {summary.data ? `${total} gaps across ${summary.data.length} categories` : 'Loading…'} ·
            click a card to review
          </p>
        </div>
        <button
          onClick={() => setUploadOpen(true)}
          className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50"
        >
          Upload Excel
        </button>
      </div>

      {uploadOpen && <UploadModal onClose={() => setUploadOpen(false)} />}

      {summary.isError && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          Could not load gaps. Is the backend running on :8000?
        </div>
      )}

      {summary.data && summary.data.length === 0 && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-6 text-center text-sm text-emerald-700">
          No gaps detected 🎉
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {summary.data?.map((s) => (
          <GapCard key={s.gap_type} s={s} onClick={() => navigate(`/gaps/${s.gap_type}`)} />
        ))}
      </div>
    </section>
  )
}
