import { useQuery } from '@tanstack/react-query'
import { fetchPoliticianDetail } from '../api/endpoints'

export function usePoliticianDetail(id: string) {
  return useQuery({
    queryKey: ['politician', id],
    queryFn: () => fetchPoliticianDetail(id),
    enabled: !!id,
  })
}
