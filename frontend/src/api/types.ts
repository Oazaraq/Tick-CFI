export type Priority = 'low' | 'medium' | 'high' | 'critical'
export type ActionStatus = 'todo' | 'in_progress' | 'blocked' | 'done' | 'cancelled'
export type Role = 'admin' | 'project_manager' | 'contributor' | 'reader'

export const PRIORITIES: Priority[] = ['low', 'medium', 'high', 'critical']
export const ACTION_STATUSES: ActionStatus[] = ['todo', 'in_progress', 'blocked', 'done', 'cancelled']
export const ROLES: Role[] = ['admin', 'project_manager', 'contributor', 'reader']
export const isClosed = (s: ActionStatus) => s === 'done' || s === 'cancelled'

export interface UserBrief { id: number; first_name: string; last_name: string; is_active: boolean }
export interface User extends UserBrief { email: string; role: Role; notifications_enabled: boolean }
export interface Me extends User { permissions: string[]; due_soon_days: number; done_hide_days: number }
export interface Status { id: number; code: string; label: string; position: number; is_active_counted: boolean }

export interface ProjectCard {
  id: number
  title: string
  status_code: string
  position: number
  priority: Priority
  owner: UserBrief
  due_date: string | null
  end_date: string | null
  blocked_reason: string | null
  blocked_since: string | null
  actions_total: number
  actions_done: number
  actions_overdue: number
  actions_open: number
  days_sold: number
  days_consumed: number
}

export interface Project extends ProjectCard {
  description: string | null
  start_date: string | null
  status_label: string
  members: UserBrief[]
  created_at: string
}

export interface Action {
  id: number
  project_id: number
  title: string
  description: string | null
  assignee: UserBrief | null
  due_date: string | null
  priority: Priority
  status: ActionStatus
  origin: string
  sourcing: Sourcing
  subcontractor: string | null
  meeting_id: number | null
  closed_at: string | null
  created_at: string
  project_title: string
  is_overdue: boolean
}

export type RiskLevel = 'low' | 'medium' | 'high'
export type RiskStatus = 'open' | 'watched' | 'mitigated' | 'closed' | 'occurred'
export const RISK_LEVELS: RiskLevel[] = ['low', 'medium', 'high']
export const RISK_STATUSES: RiskStatus[] = ['open', 'watched', 'mitigated', 'closed', 'occurred']

export interface Risk {
  id: number
  project_id: number
  title: string
  description: string | null
  mitigation: string | null
  probability: RiskLevel
  impact: RiskLevel
  owner: UserBrief | null
  status: RiskStatus
  score: number
  criticity: RiskLevel
  created_at: string
}

export interface Comment { id: number; project_id: number; author: UserBrief; body: string; created_at: string; edited_at: string | null }
export interface DocLink { id: number; project_id: number; label: string; url: string; author: UserBrief; created_at: string }
export type Sourcing = 'internal' | 'external'
export interface PlanningItem {
  id: number
  project_id: number
  label: string
  kind: 'phase' | 'milestone'
  start_date: string
  end_date: string
  position: number
  category: string | null
  days_sold: number | null
  days_consumed: number | null
  predecessor_ids: number[]
  dependency_issues: number[]
}
export interface Category { code: string; label: string }
export interface Effort { categories: (Category & { sold: number; consumed: number })[]; sold: number; consumed: number }

export interface Zone<T> { total: number; items: T[] }
export interface BlockedProject { id: number; title: string; blocked_reason: string | null; blocked_since: string | null }
export type TileKey = 'active_projects' | 'open_actions' | 'overdue_actions' | 'blocked_projects' | 'my_actions'
export interface Dashboard {
  tiles: Record<TileKey, number>
  due_soon: Zone<Action>
  blocked_projects: Zone<BlockedProject>
  unassigned: Zone<Action>
  inactive_assignee: Zone<Action>
  no_due_date: number
  charts: DashboardCharts
}

export interface DashboardCharts {
  projects_by_status: { code: string; label: string | null; count: number }[]
  actions_by_priority: { code: Priority; count: number }[]
  overdue_by_project: { project_id: number; title: string; count: number }[]
  effort_by_project: { project_id: number; title: string; sold: number; consumed: number }[]
}

export interface HistoryEvent {
  id: number
  event_type: string
  entity_type: string
  entity_id: number
  detail: Record<string, string>
  author: UserBrief | null
  created_at: string
}

// --- Réunions et IA (lot 3) ---
export type MeetingStatus = 'processing' | 'to_validate' | 'validated' | 'failed' | 'rejected'

export interface MeetingSummary { context: string; topics: string[]; decisions: string[]; open_points: string[] }

export interface MeetingCandidate {
  title: string
  assignee_name: string | null
  assignee_id: number | null
  due_date_text: string | null
  due_date: string | null
  priority: Priority
  source_quote: string
}

export interface MeetingItem {
  id: number
  project_id: number
  title: string
  meeting_date: string
  status: MeetingStatus
  provider: string | null
  created_at: string
  actions_count: number
}

export interface Meeting extends MeetingItem {
  participants: string | null
  transcript: string
  summary: MeetingSummary | null
  candidates: MeetingCandidate[] | null
  error_message: string | null
}

// --- Fichiers et journal des emails (lot 4) ---
export interface ProjectFile {
  id: number
  project_id: number
  filename: string
  content_type: string
  size: number
  created_at: string
  uploader: UserBrief | null
}

export interface FilesList { files: ProjectFile[]; purge_on: string | null }

export interface EmailLog {
  id: number
  created_at: string
  recipient_email: string
  subject: string
  event_type: string
  project_id: number | null
  status: 'sent' | 'failed'
  error: string | null
}

/* ---------- Check-list de lancement ---------- */
export type ChecklistStatus = '' | 'ok' | 'ko' | 'tbc' | 'na'
export type ChecklistOwner = 'Avant-vente' | 'Client' | 'CFI'
export interface ChecklistItem { id: string; point: string; question: string; owner: ChecklistOwner; blocking: boolean }
export interface ChecklistCustomItem extends ChecklistItem { section: string }
export interface ChecklistSection { code: string; title: string; note?: string; calc?: boolean; items: ChecklistItem[] }
export interface ChecklistCalcRow { name: string; qty: number; watts: number | null; units: number | null }
export interface ChecklistMeta { client: string; kickoff_date: string | null; participants: string; order_ref: string }
export interface ChecklistData {
  revision: number
  meta: ChecklistMeta
  states: Record<string, { status: ChecklistStatus; note: string }>
  custom: ChecklistCustomItem[]
  calc: ChecklistCalcRow[]
}
export interface Checklist extends ChecklistData {
  sections: ChecklistSection[]
  updated_at: string | null
  updated_by: UserBrief | null
}

/** Reporting de charge : une ligne par projet et catégorie (jours ; gestion de projet : 1 j = 7,5 h). */
export interface EffortReportRow {
  project_id: number
  title: string
  status_code: string
  status_label: string
  owner: UserBrief
  category: string | null
  category_label: string
  sold: number
  consumed: number
}

