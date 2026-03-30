import { useQuery } from '@tanstack/react-query'
import { fetchGrowthRanking, fetchFamilyRanking, fetchGapRanking } from '../api/endpoints'

export function useGrowthRanking(limit = 20) {
  return useQuery({
    queryKey: ['ranking', 'growth', limit],
    queryFn: () => fetchGrowthRanking(limit),
  })
}

export function useFamilyRanking(limit = 20) {
  return useQuery({
    queryKey: ['ranking', 'family', limit],
    queryFn: () => fetchFamilyRanking(limit),
  })
}

export function useGapRanking(limit = 20) {
  return useQuery({
    queryKey: ['ranking', 'gap', limit],
    queryFn: () => fetchGapRanking(limit),
  })
}
