// ── Ranking ──

export interface RankedPolitician {
  rank: number
  politician_id: string
  name: string
  party: string | null
  constituency: string | null
  metric_value: number
  metric_label: string
  total_assets_current: number
}

export interface RankingResponse {
  ranking_type: string
  total_count: number
  items: RankedPolitician[]
}

// ── Politician Detail ──

export interface TimelinePoint {
  year: number
  total_assets: number
  net_assets: number
  real_estate: number
  deposit: number
  securities: number
  self_amount: number
  spouse_amount: number
  family_amount: number
}

export interface RealEstateGapCard {
  property_description: string
  declared_value: number
  estimated_market_value: number
  gap_amount: number
  gap_pct: number
  match_confidence: number
  match_method: string | null
}

export interface PoliticianDetail {
  id: string
  name: string
  party: string | null
  constituency: string | null
  latest_elected: number | null
  timeline: TimelinePoint[]
  real_estate_gaps: RealEstateGapCard[]
  growth_rate: number | null
  cagr: number | null
  family_contribution_ratio: number | null
  anomaly_score: number | null
}

// ── Debate ──

export interface DebateStreamEvent {
  event: string
  data: string
}

export interface AgentStartData {
  agent: string
  display_name: string
  emoji: string
}

export interface AgentTokenData {
  agent: string
  token: string
}

export interface AgentDoneData {
  agent: string
  opinion: string
  confidence: number
}

export interface DebateCompleteData {
  followup_questions: string[]
  disclaimer: string
}

export type AgentRole = 'suspicion' | 'optimist' | 'factcheck'

export interface AgentMessage {
  role: AgentRole
  displayName: string
  emoji: string
  content: string
  isComplete: boolean
  confidence: number
}
