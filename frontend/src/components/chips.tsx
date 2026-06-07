import type { GapStatus, GapType, MappingContext } from '../types'
import { GAP_CODE, GAP_LABELS } from '../types'

function Pill({ text, cls, title }: { text: string; cls: string; title?: string }) {
  return (
    <span
      title={title}
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ${cls}`}
    >
      {text}
    </span>
  )
}

const STATUS: Record<GapStatus, string> = {
  Open: 'bg-sky-50 text-sky-700 ring-sky-200',
  Accepted: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  'Not applicable': 'bg-slate-100 text-slate-500 ring-slate-200',
}

export const StatusChip = ({ status }: { status: GapStatus }) => (
  <Pill text={status} cls={STATUS[status]} />
)

const CTX: Record<MappingContext, string> = {
  Entity: 'bg-violet-50 text-violet-700 ring-violet-200',
  RP_IND: 'bg-indigo-50 text-indigo-700 ring-indigo-200',
  RP_ORG: 'bg-blue-50 text-blue-700 ring-blue-200',
}

export const ContextChip = ({ context }: { context: MappingContext }) => (
  <Pill text={context} cls={CTX[context]} />
)

export const GapTypeBadge = ({ type }: { type: GapType }) => (
  <Pill
    text={GAP_CODE[type]}
    title={GAP_LABELS[type]}
    cls="bg-brand-50 text-brand-700 ring-brand-100"
  />
)
