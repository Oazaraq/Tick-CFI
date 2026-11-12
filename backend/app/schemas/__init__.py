"""Schémas d'entrée/sortie de l'API (Pydantic v2). Les énumérations sont validées ici."""
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Priority = Literal["low", "medium", "high", "critical"]
ActionStatus = Literal["todo", "in_progress", "blocked", "done", "cancelled"]
RoleName = Literal["admin", "project_manager", "contributor", "reader"]
Title = Annotated[str, Field(min_length=1, max_length=200)]
Name = Annotated[str, Field(min_length=1, max_length=100)]
Password = Annotated[str, Field(min_length=8, max_length=200)]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserBrief(ORM):
    id: int
    first_name: str
    last_name: str
    is_active: bool


class UserOut(UserBrief):
    email: str
    role: RoleName
    notifications_enabled: bool


class MeOut(UserOut):
    permissions: list[str] = []
    due_soon_days: int = 7
    done_hide_days: int = 30


class LoginIn(BaseModel):
    email: str
    password: str


class MeUpdate(BaseModel):
    notifications_enabled: bool | None = None
    current_password: str | None = None
    new_password: Password | None = None


class UserCreate(BaseModel):
    email: Annotated[str, Field(max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")]
    first_name: Name
    last_name: Name
    role: RoleName
    password: Password | None = None  # vide : lien d'activation envoyé au compte


class PasswordForgotIn(BaseModel):
    email: Annotated[str, Field(min_length=1, max_length=255)]


class PasswordResetIn(BaseModel):
    token: Annotated[str, Field(min_length=10, max_length=500)]
    password: Password


class PasswordLinkOut(BaseModel):
    url: str
    valid_hours: int
    emailed: bool


class UserUpdate(BaseModel):
    role: RoleName | None = None
    is_active: bool | None = None
    password: Password | None = None


class StatusOut(ORM):
    id: int
    code: str
    label: str
    position: int
    is_active_counted: bool


class ProjectCard(ORM):
    id: int
    title: str
    status_code: str
    position: int
    priority: Priority
    owner: UserBrief
    due_date: date | None
    end_date: date | None
    blocked_reason: str | None
    blocked_since: datetime | None
    actions_total: int = 0
    actions_done: int = 0
    actions_overdue: int = 0
    actions_open: int = 0
    days_sold: float = 0
    days_consumed: float = 0


class ProjectOut(ProjectCard):
    description: str | None
    start_date: date | None
    status_label: str
    members: list[UserBrief]
    created_at: datetime


class ProjectCreate(BaseModel):
    title: Title
    description: str | None = None
    owner_id: int
    member_ids: list[int] = []
    priority: Priority = "medium"
    start_date: date | None = None
    due_date: date | None = None
    status_code: str = "presale"
    blocked_reason: str | None = None


class ProjectUpdate(BaseModel):
    title: Title | None = None
    description: str | None = None
    owner_id: int | None = None
    member_ids: list[int] | None = None
    priority: Priority | None = None
    start_date: date | None = None
    due_date: date | None = None


class ProjectMove(BaseModel):
    status_code: str
    position: int | None = None
    blocked_reason: str | None = None
    confirm: bool = False


Sourcing = Literal["internal", "external"]
Subcontractor = Annotated[str, Field(max_length=200)]


class ActionCreate(BaseModel):
    title: Title
    description: str | None = None
    assignee_id: int | None = None
    due_date: date | None = None
    priority: Priority = "medium"
    status: ActionStatus = "todo"
    sourcing: Sourcing = "internal"
    subcontractor: Subcontractor | None = None


class ActionUpdate(BaseModel):
    title: Title | None = None
    description: str | None = None
    assignee_id: int | None = None
    due_date: date | None = None
    priority: Priority | None = None
    status: ActionStatus | None = None
    sourcing: Sourcing | None = None
    subcontractor: Subcontractor | None = None


class ActionOut(ORM):
    id: int
    project_id: int
    title: str
    description: str | None
    assignee: UserBrief | None
    due_date: date | None
    priority: Priority
    status: ActionStatus
    origin: str
    sourcing: Sourcing
    subcontractor: str | None
    meeting_id: int | None
    closed_at: datetime | None
    created_at: datetime
    project_title: str = ""
    is_overdue: bool = False


class HistoryOut(ORM):
    id: int
    event_type: str
    entity_type: str
    entity_id: int
    detail: dict
    author: UserBrief | None
    created_at: datetime


class BlockedProject(ORM):
    id: int
    title: str
    blocked_reason: str | None
    blocked_since: datetime | None


class ActionZone(BaseModel):
    total: int
    items: list[ActionOut]


class ProjectZone(BaseModel):
    total: int
    items: list[BlockedProject]


class ChartCount(BaseModel):
    code: str
    label: str | None = None
    count: int


class ChartProjectCount(BaseModel):
    project_id: int
    title: str
    count: int


class ChartEffort(BaseModel):
    project_id: int
    title: str
    sold: float
    consumed: float


class DashboardCharts(BaseModel):
    projects_by_status: list[ChartCount]
    actions_by_priority: list[ChartCount]
    overdue_by_project: list[ChartProjectCount]
    effort_by_project: list[ChartEffort]


class DashboardOut(BaseModel):
    tiles: dict[str, int]
    due_soon: ActionZone
    blocked_projects: ProjectZone
    unassigned: ActionZone
    inactive_assignee: ActionZone
    no_due_date: int
    charts: DashboardCharts


RiskLevel = Literal["low", "medium", "high"]
RiskStatus = Literal["open", "watched", "mitigated", "closed", "occurred"]


class RiskIn(BaseModel):
    title: Title
    description: str | None = None
    mitigation: str | None = None
    probability: RiskLevel
    impact: RiskLevel
    owner_id: int | None = None
    status: RiskStatus = "open"


class RiskUpdate(BaseModel):
    title: Title | None = None
    description: str | None = None
    mitigation: str | None = None
    probability: RiskLevel | None = None
    impact: RiskLevel | None = None
    owner_id: int | None = None
    status: RiskStatus | None = None


class RiskOut(ORM):
    id: int
    project_id: int
    title: str
    description: str | None
    mitigation: str | None
    probability: RiskLevel
    impact: RiskLevel
    owner: UserBrief | None
    status: RiskStatus
    created_at: datetime
    score: int = 0
    criticity: RiskLevel = "low"


class CommentIn(BaseModel):
    body: Annotated[str, Field(min_length=1, max_length=5000)]


class CommentOut(ORM):
    id: int
    project_id: int
    author: UserBrief
    body: str
    created_at: datetime
    edited_at: datetime | None


class LinkIn(BaseModel):
    label: Title
    url: Annotated[str, Field(min_length=1, max_length=1000)]


class LinkOut(ORM):
    id: int
    project_id: int
    label: str
    url: str
    author: UserBrief
    created_at: datetime


PlanningKind = Literal["phase", "milestone"]


Days = Annotated[float, Field(ge=0, le=9999)]


class PlanningIn(BaseModel):
    label: Title
    kind: PlanningKind = "phase"
    start_date: date
    end_date: date | None = None
    category: str | None = None
    days_sold: Days | None = None
    days_consumed: Days | None = None
    predecessor_ids: list[int] = []


class PlanningUpdate(BaseModel):
    label: Title | None = None
    kind: PlanningKind | None = None
    start_date: date | None = None
    end_date: date | None = None
    category: str | None = None
    days_sold: Days | None = None
    days_consumed: Days | None = None
    predecessor_ids: list[int] | None = None


class PlanningOut(ORM):
    id: int
    project_id: int
    label: str
    kind: PlanningKind
    start_date: date
    end_date: date
    position: int
    category: str | None
    days_sold: float | None
    days_consumed: float | None
    predecessor_ids: list[int]
    dependency_issues: list[int] = []  # prédécesseurs dont l'ordre n'est pas respecté


class CategoryOut(BaseModel):
    code: str
    label: str


class EffortLine(CategoryOut):
    sold: float
    consumed: float


class EffortOut(BaseModel):
    categories: list[EffortLine]
    sold: float
    consumed: float


# --- Réunions et IA (lot 3) ---
MeetingStatus = Literal["processing", "to_validate", "validated", "failed", "rejected"]


class MeetingIn(BaseModel):
    title: Title
    meeting_date: date
    participants: list[Annotated[str, Field(max_length=200)]] = []
    transcript: Annotated[str, Field(min_length=1, max_length=2_000_000)]
    filename: str | None = None  # « .vtt » : horodatages retirés (DFB B.2)


class MeetingSummary(BaseModel):
    context: str = ""
    topics: list[str] = []
    decisions: list[str] = []
    open_points: list[str] = []


class MeetingCandidate(BaseModel):
    title: str
    assignee_name: str | None = None  # tel qu'entendu ; assignee_id vide si « non identifié »
    assignee_id: int | None = None
    due_date_text: str | None = None
    due_date: date | None = None
    priority: Priority = "medium"
    source_quote: str = ""


class MeetingItem(ORM):
    id: int
    project_id: int
    title: str
    meeting_date: date
    status: MeetingStatus
    provider: str | None
    created_at: datetime
    actions_count: int = 0


class MeetingOut(MeetingItem):
    participants: str | None
    transcript: str
    summary: MeetingSummary | None
    candidates: list[MeetingCandidate] | None
    error_message: str | None


class MeetingValidate(BaseModel):
    summary: MeetingSummary
    actions: list[ActionCreate] = []


# --- Fichiers et journal des emails (lot 4) ---
class FileOut(ORM):
    id: int
    project_id: int
    filename: str
    content_type: str
    size: int
    created_at: datetime
    uploader: UserBrief | None


class FilesOut(BaseModel):
    files: list[FileOut]
    purge_on: date | None  # date de suppression définitive si le projet est livré


class EmailLogOut(ORM):
    id: int
    created_at: datetime
    recipient_email: str
    subject: str
    event_type: str
    project_id: int | None
    status: Literal["sent", "failed"]
    error: str | None


# ---------- Check-list de lancement ----------
ChecklistStatus = Literal["", "ok", "ko", "tbc", "na"]
ChecklistOwner = Literal["Avant-vente", "Client", "CFI"]


class ChecklistMeta(BaseModel):
    client: str = Field("", max_length=200)
    kickoff_date: date | None = None
    participants: str = Field("", max_length=500)
    order_ref: str = Field("", max_length=200)


class ChecklistState(BaseModel):
    status: ChecklistStatus = ""
    note: str = Field("", max_length=2000)


class ChecklistCustomItem(BaseModel):
    id: str = Field(pattern=r"^X-[A-Za-z0-9]{1,16}$")
    section: str = Field(max_length=10)
    point: str = Field(min_length=1, max_length=120)
    question: str = Field("", max_length=500)
    owner: ChecklistOwner = "CFI"
    blocking: bool = False


class ChecklistCalcRow(BaseModel):
    name: str = Field("", max_length=120)
    qty: int = Field(1, ge=0, le=999)
    watts: float | None = Field(None, ge=0, le=100000)
    units: float | None = Field(None, ge=0, le=100)


class ChecklistIn(BaseModel):
    revision: int = Field(ge=0)
    meta: ChecklistMeta = Field(default_factory=ChecklistMeta)
    states: dict[str, ChecklistState] = Field(default_factory=dict)
    custom: list[ChecklistCustomItem] = Field(default_factory=list, max_length=50)
    calc: list[ChecklistCalcRow] = Field(default_factory=list, max_length=50)


class ChecklistOut(ChecklistIn):
    sections: list[dict]
    updated_at: datetime | None = None
    updated_by: UserBrief | None = None


class EffortReportRow(BaseModel):
    project_id: int
    title: str
    status_code: str
    status_label: str
    owner: UserBrief
    category: str | None
    category_label: str
    sold: float
    consumed: float

