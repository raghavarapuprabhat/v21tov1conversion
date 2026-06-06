// Domain types mirrored from the backend (LLD §2–§5).

export type MappingContext = 'Entity' | 'RP_IND' | 'RP_ORG'
export type GapStatus = 'Open' | 'Accepted' | 'Not applicable'
export type Severity = 'Critical' | 'High' | 'Medium' | 'Low'

export type GapType =
  | 'G1_COVERAGE'
  | 'G2_OCCURRENCE'
  | 'G3_DATATYPE'
  | 'G4_MANDATORY'
  | 'G5_REVERSE_ORPHAN'
  | 'G6_DD_MISMATCH'
  | 'G7_CARDINALITY'
  | 'G8_DUP_MAPPING'
  | 'G9_DATA_QUALITY'

export interface SourceRef {
  sheet: string
  row: number
  column?: string | null
}

export interface Gap {
  gap_id: string
  gap_type: GapType
  is_number?: string | null
  mapping_context?: MappingContext | null
  v1_path?: string | null
  v1_ref?: SourceRef | null
  v2_ref?: SourceRef | null
  v1_value?: string | null
  v2_value?: string | null
  detail: string
  flags: Record<string, unknown>
  severity: Severity
  root_node?: string | null
  dd_ref?: string | null
  dd_in_v2: boolean
  status: GapStatus
}

export interface G1Metrics {
  total_missing: number
  nullable_false: number
  parent_min1: number
}

export interface GapSummary {
  gap_type: GapType
  total: number
  by_status: Record<string, number>
  by_severity: Record<string, number>
  metrics?: G1Metrics | null
}

export interface GapPage {
  page: number
  page_size: number
  total: number
  rows: Gap[]
}

export interface Comment {
  comment_id: string
  gap_id?: string | null
  is_anchor?: string | null
  mapping_context?: MappingContext | null
  parent_comment_id?: string | null
  author: string
  body: string
  created_at: string
}

export interface CommentNode extends Comment {
  replies: CommentNode[]
}

export interface GapConversation {
  gap_id: string
  is_number?: string | null
  thread: CommentNode[]
  earlier_for_is: CommentNode[]
}

export interface StatusChange {
  gap_id: string
  old_status?: GapStatus | null
  new_status: GapStatus
  author: string
  note?: string | null
  changed_at: string
}

export interface Occurs {
  raw?: string | null
  value?: number | null
  unbounded: boolean
}

export interface TreeNode {
  name: string
  node_kind?: string | null
  min_occurs?: number | null
  max_occurs: Occurs
  is_array: boolean
  children: TreeNode[]
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  leaves: any[]
  gap_count: number
  gaps_by_type: Record<string, number>
}

// V2.1 row has 20 columns; kept loose for the Fetch-V2-By-DD viewer.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type V2Field = Record<string, any>

export interface SavedView {
  view_id: string
  name: string
  owner?: string | null
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  spec: Record<string, any>
}

export const GAP_LABELS: Record<GapType, string> = {
  G1_COVERAGE: 'Coverage',
  G2_OCCURRENCE: 'Occurrence',
  G3_DATATYPE: 'Data type',
  G4_MANDATORY: 'Mandatory / Optional',
  G5_REVERSE_ORPHAN: 'Reverse orphan',
  G6_DD_MISMATCH: 'DD mismatch',
  G7_CARDINALITY: 'Cardinality',
  G8_DUP_MAPPING: 'Duplicate mapping',
  G9_DATA_QUALITY: 'Data quality',
}

export const GAP_CODE: Record<GapType, string> = {
  G1_COVERAGE: 'G1',
  G2_OCCURRENCE: 'G2',
  G3_DATATYPE: 'G3',
  G4_MANDATORY: 'G4',
  G5_REVERSE_ORPHAN: 'G5',
  G6_DD_MISMATCH: 'G6',
  G7_CARDINALITY: 'G7',
  G8_DUP_MAPPING: 'G8',
  G9_DATA_QUALITY: 'G9',
}
