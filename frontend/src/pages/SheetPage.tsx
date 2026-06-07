import SheetGrid from '../components/SheetGrid'

export default function SheetPage({ which }: { which: 'v1' | 'v2' }) {
  const isV2 = which === 'v2'
  return (
    <section className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
          {isV2 ? 'V2.1 Workbook' : 'V1 Workbook'}
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          {isV2
            ? 'The uploaded V2.1 sheet as is. Every column is filterable; edit any cell inline and download the updated workbook.'
            : 'The uploaded V1 sheet as is — read-only. Every column has a searchable multi-select filter.'}
        </p>
      </div>
      <SheetGrid which={which} editable={isV2} downloadName={isV2 ? 'v2.1_edited.xlsx' : undefined} />
    </section>
  )
}
