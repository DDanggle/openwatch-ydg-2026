// 정적 빌드 모드: /data/*.json 에서 직접 읽음 (Vercel 배포용)
const DATA_BASE = '/data'

export async function fetchApi<T>(path: string): Promise<T> {
  // API 경로 → 정적 JSON 파일 매핑
  const jsonMap: Record<string, string> = {
    '/rankings/growth': '/ranking_growth.json',
    '/rankings/family-contribution': '/ranking_family.json',
    '/rankings/real-estate-gap': '/ranking_gap.json',
    '/rankings/gap/distribution': '/gap_distribution.json',
  }

  // 쿼리 파라미터 제거
  const cleanPath = path.split('?')[0]

  // 매핑된 파일이 있으면 정적 JSON 사용
  const jsonPath = jsonMap[cleanPath]
  if (jsonPath) {
    const res = await fetch(`${DATA_BASE}${jsonPath}`)
    if (!res.ok) throw new Error(`Static file error: ${res.status}`)
    return res.json()
  }

  // politician detail
  const polMatch = cleanPath.match(/^\/politicians\/(.+)$/)
  if (polMatch) {
    const res = await fetch(`${DATA_BASE}/politicians.json`)
    if (!res.ok) throw new Error(`Static file error: ${res.status}`)
    const all = await res.json()
    const pol = all[polMatch[1]]
    if (!pol) throw new Error('Not found')
    return pol as T
  }

  throw new Error(`No static data for: ${path}`)
}

export async function postApi<T>(path: string, body: unknown): Promise<T> {
  // 정적 모드에서는 POST 비활성 (에이전트 토론 등)
  throw new Error('POST not available in static mode')
}
