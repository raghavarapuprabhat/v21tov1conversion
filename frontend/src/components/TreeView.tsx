import { useState } from 'react'
import type { TreeNode } from '../types'

function NodeRow({ node, depth }: { node: TreeNode; depth: number }) {
  const [open, setOpen] = useState(depth < 3)
  const hasChildren = node.children.length > 0
  const leaves = node.leaves ?? []
  const expandable = hasChildren || leaves.length > 0

  return (
    <div>
      <div
        className="flex items-center gap-2 rounded-md px-2 py-1 hover:bg-slate-50"
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
      >
        {expandable ? (
          <button onClick={() => setOpen((v) => !v)} className="w-4 text-slate-400">
            {open ? '▾' : '▸'}
          </button>
        ) : (
          <span className="w-4" />
        )}
        <span className="text-sm font-medium text-slate-800">{node.name}</span>
        {node.node_kind && (
          <span className="rounded bg-slate-100 px-1.5 text-[10px] uppercase tracking-wide text-slate-500">
            {node.node_kind}
          </span>
        )}
        {node.is_array && (
          <span className="rounded bg-indigo-50 px-1.5 text-[10px] font-medium text-indigo-600">[ ] array</span>
        )}
        {typeof node.min_occurs === 'number' && (
          <span className="text-[10px] text-slate-400">
            min {node.min_occurs}/max {node.max_occurs.unbounded ? '∞' : node.max_occurs.value ?? '—'}
          </span>
        )}
        {leaves.length > 0 && (
          <span className="text-[10px] text-slate-400">{leaves.length} fields</span>
        )}
        {node.gap_count > 0 && (
          <span className="ml-auto rounded-full bg-rose-50 px-2 text-[11px] font-medium text-rose-600 ring-1 ring-rose-200">
            {node.gap_count} gaps
          </span>
        )}
      </div>

      {open && leaves.length > 0 && (
        <div style={{ paddingLeft: `${depth * 16 + 28}px` }} className="flex flex-wrap gap-1.5 py-1">
          {leaves.map((l, i) => (
            <span
              key={i}
              title={l.xsd_type_raw ?? ''}
              className="rounded bg-slate-50 px-1.5 py-0.5 text-[11px] text-slate-600 ring-1 ring-slate-200"
            >
              {l.is_number ? `${l.is_number} · ` : ''}{l.attribute ?? '?'}
            </span>
          ))}
        </div>
      )}

      {open && hasChildren && node.children.map((c, i) => <NodeRow key={i} node={c} depth={depth + 1} />)}
    </div>
  )
}

export default function TreeView({ root }: { root: TreeNode }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-2">
      {root.children.map((c, i) => (
        <NodeRow key={i} node={c} depth={0} />
      ))}
    </div>
  )
}
