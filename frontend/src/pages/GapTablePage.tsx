import { useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import ConversationPanel from '../components/ConversationPanel'
import DataGrid from '../components/DataGrid'
import { GapTypeBadge } from '../components/chips'
import type { Gap, GapType } from '../types'
import { GAP_LABELS } from '../types'

export default function GapTablePage() {
  const { type } = useParams()
  const [searchParams] = useSearchParams()
  const [selected, setSelected] = useState<Gap | null>(null)
  const gapType = type as GapType | undefined

  return (
    <section className="space-y-4">
      <div className="flex items-center gap-3">
        <Link to="/" className="text-sm text-brand-600 hover:text-brand-700">← Gaps</Link>
        {gapType && <GapTypeBadge type={gapType} />}
        <h1 className="text-xl font-semibold tracking-tight text-slate-900">
          {gapType ? GAP_LABELS[gapType] : 'All gaps'}
        </h1>
      </div>

      <DataGrid type={type} onOpen={setSelected} autoOpen={searchParams.get('open') ?? undefined} />

      {selected && <ConversationPanel gap={selected} onClose={() => setSelected(null)} />}
    </section>
  )
}
