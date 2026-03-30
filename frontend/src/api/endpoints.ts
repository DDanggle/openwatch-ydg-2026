import { fetchApi } from './client'
import type { RankingResponse, PoliticianDetail } from './types'

export function fetchGrowthRanking(limit = 20) {
  return fetchApi<RankingResponse>(`/rankings/growth?limit=${limit}`)
}

export function fetchFamilyRanking(limit = 20) {
  return fetchApi<RankingResponse>(`/rankings/family-contribution?limit=${limit}`)
}

export function fetchGapRanking(limit = 20) {
  return fetchApi<RankingResponse>(`/rankings/real-estate-gap?limit=${limit}`)
}

export function fetchPoliticianDetail(id: string) {
  return fetchApi<PoliticianDetail>(`/politicians/${id}`)
}
