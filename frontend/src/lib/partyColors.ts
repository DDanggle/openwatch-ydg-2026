export const PARTY_COLORS: Record<string, string> = {
  '더불어민주당': '#1B56FD',
  '국민의힘': '#E02D2D',
  '조국혁신당': '#0D47A1',
  '개혁신당': '#FF6F00',
  '진보당': '#D50000',
  '기본소득당': '#00897B',
  '무소속': '#9E9E9E',
  '국회': '#6B7280',
  '기타': '#9E9E9E',
}

export function getPartyColor(party: string | null): string {
  if (!party) return '#9E9E9E'
  return PARTY_COLORS[party] || '#6B7280'
}
