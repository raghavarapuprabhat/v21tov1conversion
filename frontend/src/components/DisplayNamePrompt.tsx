import { useState } from 'react'
import { useDisplayName } from '../state/displayName'

// Captures a display name once (no auth this phase). Stored in localStorage and
// attached as `author` on comments/status changes (LLD §9.2).
export default function DisplayNamePrompt() {
  const { name, setName } = useDisplayName()
  const [draft, setDraft] = useState('')
  if (name) return null

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-slate-900/40 backdrop-blur-sm">
      <div className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-xl ring-1 ring-slate-200">
        <h2 className="text-lg font-semibold text-slate-900">Welcome 👋</h2>
        <p className="mt-1 text-sm text-slate-500">
          Enter a display name so your comments and dispositions are attributed.
          (No login this phase.)
        </p>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            if (draft.trim()) setName(draft.trim())
          }}
          className="mt-4 flex gap-2"
        >
          <input
            autoFocus
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="e.g. Jane Doe"
            className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
          />
          <button
            type="submit"
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-40"
            disabled={!draft.trim()}
          >
            Continue
          </button>
        </form>
      </div>
    </div>
  )
}
