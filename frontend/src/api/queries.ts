import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiGet, apiSend, apiUpload } from './client'
import type {
  Gap,
  GapConversation,
  GapPage,
  GapStatus,
  GapSummary,
  SavedView,
  StatusChange,
  TreeNode,
  V2Field,
} from '../types'

export interface Health {
  status: string
  version: string
  storage: string
  optional_gaps: boolean
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function qs(params: Record<string, any>): string {
  const u = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (Array.isArray(v)) v.forEach((item) => u.append(k, String(item)))
    else if (v !== undefined && v !== null && v !== '') u.append(k, String(v))
  })
  const s = u.toString()
  return s ? `?${s}` : ''
}

export interface Facets {
  is_numbers: string[]
  paths: string[]
}

export interface SheetGrid {
  sheet: string
  columns: string[]
  rows: Record<string, string>[]
}

export const useSheet = (which: 'v1' | 'v2') =>
  useQuery({ queryKey: ['sheet', which], queryFn: () => apiGet<SheetGrid>(`/sheets/${which}`) })

export const useFacets = (type?: string) =>
  useQuery({
    queryKey: ['facets', type],
    queryFn: () => apiGet<Facets>('/facets' + qs({ type })),
  })

export const useHealth = () =>
  useQuery({ queryKey: ['health'], queryFn: () => apiGet<Health>('/health') })

export const useSummary = () =>
  useQuery({ queryKey: ['summary'], queryFn: () => apiGet<GapSummary[]>('/summary') })

export interface GapsParams {
  type?: string
  status?: string
  context?: string
  is?: string
  is_in?: string[]
  path_in?: string[]
  v1?: string
  v2?: string
  detail?: string
  dd?: string
  dd_in_v2?: string
  nullable?: string
  root?: string
  search?: string
  sort?: string
  page?: number
  page_size?: number
}

export const useGaps = (params: GapsParams) =>
  useQuery({ queryKey: ['gaps', params], queryFn: () => apiGet<GapPage>('/gaps' + qs(params)) })

export const useConversation = (gapId: string | null) =>
  useQuery({
    queryKey: ['conversation', gapId],
    queryFn: () => apiGet<GapConversation>(`/gaps/${gapId}/comments`),
    enabled: !!gapId,
  })

export const useHistory = (gapId: string | null) =>
  useQuery({
    queryKey: ['history', gapId],
    queryFn: () => apiGet<StatusChange[]>(`/gaps/${gapId}/history`),
    enabled: !!gapId,
  })

export const useTree = () =>
  useQuery({ queryKey: ['tree'], queryFn: () => apiGet<TreeNode>('/tree') })

export const useV2ByDd = (dd: string | null) =>
  useQuery({
    queryKey: ['v2dd', dd],
    queryFn: () => apiGet<V2Field[]>(`/v2/by-dd/${dd}`),
    enabled: !!dd,
  })

export const useViews = () =>
  useQuery({ queryKey: ['views'], queryFn: () => apiGet<SavedView[]>('/views') })

// --- mutations ---------------------------------------------------------------

export function useSetStatus() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (v: { gapId: string; status: GapStatus; author: string; note?: string }) =>
      apiSend<Gap>(`/gaps/${v.gapId}/status`, 'PATCH', {
        status: v.status,
        author: v.author,
        note: v.note,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['gaps'] })
      qc.invalidateQueries({ queryKey: ['summary'] })
      qc.invalidateQueries({ queryKey: ['history'] })
    },
  })
}

export function useBulkStatus() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (v: { gapIds: string[]; status: GapStatus; author: string; note?: string }) =>
      apiSend<{ updated: number }>('/gaps/bulk-status', 'PATCH', {
        gap_ids: v.gapIds,
        status: v.status,
        author: v.author,
        note: v.note,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['gaps'] })
      qc.invalidateQueries({ queryKey: ['summary'] })
    },
  })
}

export function useAddComment() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (v: { gapId: string; author: string; body: string; parent_comment_id?: string }) =>
      apiSend(`/gaps/${v.gapId}/comments`, 'POST', {
        author: v.author,
        body: v.body,
        parent_comment_id: v.parent_comment_id,
      }),
    onSuccess: (_d, v) => {
      qc.invalidateQueries({ queryKey: ['conversation', v.gapId] })
    },
  })
}

export function useSaveView() {
  const qc = useQueryClient()
  return useMutation({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    mutationFn: (v: { name: string; spec: Record<string, any> }) =>
      apiSend<SavedView>('/views', 'POST', v),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['views'] }),
  })
}

export interface IngestReport {
  v1_path: string
  v2_path: string
  v1_rows: number
  v2_rows: number
  reingest?: { comments_retained?: number; comments_orphaned?: number } | null
}

function invalidateAfterIngest(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: ['summary'] })
  qc.invalidateQueries({ queryKey: ['gaps'] })
  qc.invalidateQueries({ queryKey: ['tree'] })
  qc.invalidateQueries({ queryKey: ['facets'] })
  qc.invalidateQueries({ queryKey: ['sheet'] })
}

export function useIngest() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => apiSend('/ingest', 'POST'),
    onSuccess: () => invalidateAfterIngest(qc),
  })
}

export function useIngestUpload() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (v: { v1?: File | null; v2?: File | null }) => {
      const form = new FormData()
      if (v.v1) form.append('v1', v.v1)
      if (v.v2) form.append('v2', v.v2)
      return apiUpload<IngestReport>('/ingest/upload', form)
    },
    onSuccess: () => invalidateAfterIngest(qc),
  })
}
