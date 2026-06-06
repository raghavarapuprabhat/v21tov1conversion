import { useTree } from '../api/queries'
import TreeView from '../components/TreeView'

export default function TreePage() {
  const tree = useTree()
  return (
    <section className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">V1 Schema Tree</h1>
        <p className="mt-1 text-sm text-slate-500">
          Built from the V1 Node + Level columns. Gap counts roll up per node; array nodes are marked.
        </p>
      </div>
      {tree.isLoading && <p className="text-sm text-slate-400">Loading…</p>}
      {tree.isError && <p className="text-sm text-rose-600">Could not load the tree.</p>}
      {tree.data && <TreeView root={tree.data} />}
    </section>
  )
}
