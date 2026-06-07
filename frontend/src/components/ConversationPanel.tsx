import { useState } from 'react'
import { useAddComment, useConversation, useHistory, useSetStatus } from '../api/queries'
import { useDisplayName } from '../state/displayName'
import type { CommentNode, Gap, GapStatus } from '../types'
import { ContextChip, GapTypeBadge, StatusChip } from './chips'
import FetchV2ByDDModal from './FetchV2ByDDModal'

const STATUSES: GapStatus[] = ['Open', 'Accepted', 'Not applicable']

function timeAgo(iso: string) {
  const d = new Date(iso)
  return isNaN(d.getTime()) ? iso : d.toLocaleString()
}

function CommentItem({
  node,
  onReply,
}: {
  node: CommentNode
  onReply: (parentId: string, body: string) => void
}) {
  const [replying, setReplying] = useState(false)
  const [body, setBody] = useState('')
  return (
    <div className="mt-3">
      <div className="rounded-xl bg-slate-50 px-3 py-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-800">{node.author}</span>
          <span className="text-[11px] text-slate-400">{timeAgo(node.created_at)}</span>
        </div>
        <p className="mt-1 whitespace-pre-wrap text-sm text-slate-700">{node.body}</p>
        <button
          onClick={() => setReplying((v) => !v)}
          className="mt-1 text-[11px] font-medium text-brand-600 hover:underline"
        >
          Reply
        </button>
      </div>
      {replying && (
        <form
          className="ml-4 mt-2 flex gap-2"
          onSubmit={(e) => {
            e.preventDefault()
            if (body.trim()) {
              onReply(node.comment_id, body.trim())
              setBody('')
              setReplying(false)
            }
          }}
        >
          <input
            autoFocus
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="Write a reply…"
            className="flex-1 rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
          />
          <button className="rounded-lg bg-brand-600 px-3 text-sm text-white hover:bg-brand-700">Send</button>
        </form>
      )}
      {node.replies.length > 0 && (
        <div className="ml-4 border-l-2 border-slate-100 pl-3">
          {node.replies.map((r) => (
            <CommentItem key={r.comment_id} node={r} onReply={onReply} />
          ))}
        </div>
      )}
    </div>
  )
}

export default function ConversationPanel({ gap, onClose }: { gap: Gap; onClose: () => void }) {
  const { name } = useDisplayName()
  const conv = useConversation(gap.gap_id)
  const history = useHistory(gap.gap_id)
  const setStatus = useSetStatus()
  const addComment = useAddComment()
  const [body, setBody] = useState('')
  const [showV2, setShowV2] = useState(false)

  const postRoot = () => {
    if (body.trim()) {
      addComment.mutate({ gapId: gap.gap_id, author: name || 'anon', body: body.trim() })
      setBody('')
    }
  }
  const postReply = (parentId: string, text: string) =>
    addComment.mutate({ gapId: gap.gap_id, author: name || 'anon', body: text, parent_comment_id: parentId })

  return (
    <aside className="fixed inset-y-0 right-0 z-40 flex w-full max-w-md flex-col border-l border-slate-200 bg-white shadow-2xl">
      <header className="flex items-start justify-between border-b border-slate-200 p-4">
        <div>
          <div className="flex items-center gap-2">
            <GapTypeBadge type={gap.gap_type} />
            {gap.mapping_context && <ContextChip context={gap.mapping_context} />}
          </div>
          <h3 className="mt-2 text-sm font-semibold text-slate-900">
            {gap.is_number ?? '—'} <span className="font-normal text-slate-400">·</span>{' '}
            <span className="font-normal text-slate-600">{gap.detail}</span>
          </h3>
        </div>
        <button onClick={onClose} className="rounded-md p-1 text-slate-400 hover:bg-slate-100">✕</button>
      </header>

      <div className="flex-1 space-y-5 overflow-auto p-4">
        {/* compare */}
        <div className="grid grid-cols-2 gap-3 text-sm">
          <Field label="V1" value={gap.v1_value} />
          <Field label="V2.1" value={gap.v2_value} />
        </div>

        {/* status + fetch v2 */}
        <div className="flex items-center gap-2">
          <label className="text-xs font-medium text-slate-500">Status</label>
          <select
            value={gap.status}
            onChange={(e) =>
              setStatus.mutate({ gapId: gap.gap_id, status: e.target.value as GapStatus, author: name || 'anon' })
            }
            className="rounded-lg border border-slate-300 px-2 py-1 text-sm outline-none focus:border-brand-500"
          >
            {STATUSES.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          {gap.dd_ref && gap.dd_in_v2 && (
            <button
              onClick={() => setShowV2(true)}
              className="ml-auto rounded-lg border border-brand-200 bg-brand-50 px-2.5 py-1 text-xs font-medium text-brand-700 hover:bg-brand-100"
            >
              Fetch V2 by DD {gap.dd_ref}
            </button>
          )}
          {gap.dd_ref && !gap.dd_in_v2 && (
            <span className="ml-auto text-xs text-slate-400" title="This DD number is not present in V2.1">
              DD {gap.dd_ref} · not in V2.1
            </span>
          )}
        </div>

        {/* conversation */}
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Conversation</h4>
          {conv.data?.thread.length === 0 && (
            <p className="mt-2 text-sm text-slate-400">No comments yet. Start the discussion.</p>
          )}
          {conv.data?.thread.map((n) => (
            <CommentItem key={n.comment_id} node={n} onReply={postReply} />
          ))}
        </div>

        {/* earlier discussion retained for this IS (F13) */}
        {conv.data && conv.data.earlier_for_is.length > 0 && (
          <div className="rounded-xl border border-amber-200 bg-amber-50/50 p-3">
            <h4 className="text-xs font-semibold text-amber-700">
              Earlier discussion for IS {conv.data.is_number}
            </h4>
            {conv.data.earlier_for_is.map((n) => (
              <CommentItem key={n.comment_id} node={n} onReply={postReply} />
            ))}
          </div>
        )}

        {/* history */}
        {history.data && history.data.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Status history</h4>
            <ul className="mt-2 space-y-1 text-xs text-slate-500">
              {history.data.map((h, i) => (
                <li key={i}>
                  <StatusChip status={h.new_status} /> by {h.author} · {timeAgo(h.changed_at)}
                  {h.note ? ` — ${h.note}` : ''}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* new comment */}
      <footer className="border-t border-slate-200 p-3">
        <div className="flex gap-2">
          <input
            value={body}
            onChange={(e) => setBody(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && postRoot()}
            placeholder={`Comment as ${name || 'anon'}…`}
            className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
          />
          <button
            onClick={postRoot}
            className="rounded-lg bg-brand-600 px-4 text-sm font-medium text-white hover:bg-brand-700"
          >
            Post
          </button>
        </div>
      </footer>

      {showV2 && gap.dd_ref && <FetchV2ByDDModal dd={gap.dd_ref} onClose={() => setShowV2(false)} />}
    </aside>
  )
}

function Field({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="rounded-lg bg-slate-50 p-2">
      <div className="text-[10px] uppercase tracking-wide text-slate-400">{label}</div>
      <div className="mt-0.5 break-words font-medium text-slate-800">
        {value ?? <span className="text-slate-300">—</span>}
      </div>
    </div>
  )
}
