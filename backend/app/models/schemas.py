from __future__ import annotations

from pydantic import BaseModel


# ── OpenWatch API response models ──


class PaginatedResponse(BaseModel):
    totalCount: int = 0
    rows: list[dict] = []


# ── Internal domain models ──


class PoliticianSummary(BaseModel):
    id: str
    name: str
    party: str | None = None
    constituency: str | None = None
    latest_elected: int | None = None


class AssetItem(BaseModel):
    id: int | None = None
    politician_id: str
    disclosure_date: str
    disclosure_year: int
    asset_type: str
    relation: str
    kind: str | None = None
    detail: str | None = None
    origin_valuation: int = 0
    increased_amount: int = 0
    decreased_amount: int = 0
    current_valuation: int = 0
    reason: str | None = None


class YearlyAggregate(BaseModel):
    politician_id: str
    disclosure_year: int
    total_assets: int = 0
    total_debt: int = 0
    net_assets: int = 0
    real_estate_total: int = 0
    deposit_total: int = 0
    securities_total: int = 0
    self_total: int = 0
    spouse_total: int = 0
    family_total: int = 0
    yoy_change: int = 0
    yoy_change_pct: float = 0.0


# ── API response models ──


class RankedPolitician(BaseModel):
    rank: int
    politician_id: str
    name: str
    party: str | None = None
    constituency: str | None = None
    metric_value: float
    metric_label: str
    total_assets_current: int = 0


class RankingResponse(BaseModel):
    ranking_type: str
    total_count: int
    items: list[RankedPolitician]


class TimelinePoint(BaseModel):
    year: int
    total_assets: int = 0
    net_assets: int = 0
    real_estate: int = 0
    deposit: int = 0
    securities: int = 0
    self_amount: int = 0
    spouse_amount: int = 0
    family_amount: int = 0


class RealEstateGapCard(BaseModel):
    property_description: str
    declared_value: int
    estimated_market_value: int
    gap_amount: int
    gap_pct: float
    match_confidence: float
    match_method: str | None = None


class PoliticianDetail(BaseModel):
    id: str
    name: str
    party: str | None = None
    constituency: str | None = None
    latest_elected: int | None = None
    timeline: list[TimelinePoint] = []
    real_estate_gaps: list[RealEstateGapCard] = []
    growth_rate: float | None = None
    cagr: float | None = None
    family_contribution_ratio: float | None = None
    anomaly_score: float | None = None


# ── Debate models ──


class DebateRequest(BaseModel):
    politician_id: str
    topic: str | None = None  # "부동산 영향", "주식 영향", "가족 자산", "상속·증여 시그널"


class FollowupRequest(BaseModel):
    politician_id: str
    question: str
    previous_opinions: dict[str, str] = {}


class AgentOpinion(BaseModel):
    agent_name: str
    display_name: str
    emoji: str
    opinion: str
    confidence: float = 0.0
    signals: list[str] = []


class DebateResult(BaseModel):
    opinions: list[AgentOpinion]
    followup_questions: list[str] = []
    disclaimer: str = (
        "이 해석은 공개 신고자료와 실거래 데이터를 바탕으로 한 추정입니다. "
        "법률적 판단이나 사실 확정은 아닙니다."
    )


# ── Evidence Bundle (에이전트 입력) ──


class AssetTimelineEntry(BaseModel):
    year: int
    total_amount: int
    net_amount: int
    breakdown_by_type: dict[str, int] = {}
    breakdown_by_family: dict[str, int] = {}


class AssetChangeEvent(BaseModel):
    year: int
    category: str
    relation: str
    description: str | None = None
    previous_amount: int = 0
    current_amount: int = 0
    change_amount: int = 0
    change_pct: float = 0.0


class ComputedMetrics(BaseModel):
    cagr: float | None = None
    absolute_growth: int = 0
    growth_rate: float = 0.0
    family_contribution_ratio: float = 0.0
    spouse_contribution_ratio: float = 0.0
    real_estate_share: float = 0.0
    avg_gap_pct: float | None = None
    anomaly_score: float = 0.0
    anomaly_flags: dict[str, bool] = {}


class EvidenceBundle(BaseModel):
    politician_name: str
    party: str | None = None
    district: str | None = None
    timeline: list[AssetTimelineEntry] = []
    significant_changes: list[AssetChangeEvent] = []
    metrics: ComputedMetrics = ComputedMetrics()
    market_context: dict | None = None
