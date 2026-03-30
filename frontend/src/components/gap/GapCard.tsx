import { formatWon } from '../../lib/formatters'

interface GapItem {
  id: number
  politician_name: string
  politician_position: string | null
  apartment_name: string | null
  location: string
  area_sqm: number | null
  declared_value: number
  estimated_value: number
  gap_amount: number
  gap_pct: number
  match_confidence: number
  match_method: string | null
  trade_date?: string | null
  share_ratio?: number | null
  source?: string | null
  note?: string | null
}

interface Props {
  item: GapItem
  rank: number
  maxEstimated: number  // 바 차트 스케일용
}

function getGapBadge(pct: number): { text: string; bg: string; color: string } {
  if (pct >= 100) return { text: '높음', bg: 'bg-red-100', color: 'text-red-700' }
  if (pct >= 50) return { text: '주의', bg: 'bg-orange-100', color: 'text-orange-700' }
  if (pct > 0) return { text: '보통', bg: 'bg-yellow-100', color: 'text-yellow-700' }
  return { text: '정상', bg: 'bg-green-100', color: 'text-green-700' }
}

export default function GapCard({ item, rank, maxEstimated }: Props) {
  const badge = getGapBadge(item.gap_pct)
  const declaredPct = maxEstimated > 0 ? (item.declared_value / maxEstimated) * 100 : 0
  const estimatedPct = maxEstimated > 0 ? (item.estimated_value / maxEstimated) * 100 : 0

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-5 hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <span className="text-xs font-bold text-slate-300 w-6">#{rank}</span>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-slate-800">
                {item.apartment_name || '부동산'}
              </span>
              {item.area_sqm && (
                <span className="text-xs text-slate-400">{item.area_sqm.toFixed(0)}㎡</span>
              )}
            </div>
            <div className="text-xs text-slate-400 mt-0.5">
              {item.location}
            </div>
          </div>
        </div>
        <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${badge.bg} ${badge.color}`}>
          {badge.text}
        </span>
      </div>

      {/* Owner */}
      <div className="text-xs text-slate-500 mb-4">
        소유: <span className="font-medium text-slate-700">{item.politician_name}</span>
        {item.politician_position && (
          <span className="text-slate-400"> ({item.politician_position})</span>
        )}
      </div>

      {/* Horizontal bar comparison */}
      <div className="space-y-2.5 mb-4">
        {/* 신고가 */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-[11px] font-medium text-slate-500">신고가</span>
            <span className="text-sm font-bold text-slate-600">{formatWon(item.declared_value)}</span>
          </div>
          <div className="h-6 bg-slate-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-slate-400 rounded-full transition-all duration-500"
              style={{ width: `${Math.max(declaredPct, 2)}%` }}
            />
          </div>
        </div>

        {/* 실거래 추정 */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-[11px] font-medium text-blue-600">실거래 추정</span>
            <span className="text-sm font-bold text-blue-600">{formatWon(item.estimated_value)}</span>
          </div>
          <div className="h-6 bg-blue-50 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 rounded-full transition-all duration-500"
              style={{ width: `${Math.max(estimatedPct, 2)}%` }}
            />
          </div>
        </div>
      </div>

      {/* Gap highlight */}
      <div className="flex items-center justify-between pt-3 border-t border-slate-100">
        <div>
          <span className="text-xs text-slate-400">괴리 </span>
          <span className={`text-lg font-black ${item.gap_pct > 0 ? 'text-red-600' : 'text-green-600'}`}>
            {item.gap_pct > 0 ? '+' : ''}{formatWon(item.gap_amount)}
          </span>
          <span className={`text-sm font-bold ml-1 ${item.gap_pct > 0 ? 'text-red-500' : 'text-green-500'}`}>
            ({item.gap_pct > 0 ? '+' : ''}{item.gap_pct.toFixed(0)}%)
          </span>
        </div>
      </div>

      {/* Metadata row */}
      <div className="mt-2 pt-2 border-t border-slate-50 flex flex-wrap items-center gap-x-3 gap-y-1">
        {item.trade_date && (
          <span className="text-[10px] text-slate-400">
            실거래 기준: {item.trade_date}
          </span>
        )}
        {item.share_ratio && item.share_ratio < 1 && (
          <span className="text-[10px] px-1.5 py-0.5 bg-purple-50 text-purple-500 rounded">
            공유지분 {(item.share_ratio * 100).toFixed(0)}% 보정
          </span>
        )}
        <span className="text-[10px] text-slate-300">
          매칭: {item.match_method} ({(item.match_confidence * 100).toFixed(0)}%)
        </span>
        <span className={`text-[10px] ml-auto ${item.source?.includes('수동') ? 'text-purple-400' : 'text-slate-300'}`}>
          {item.source || '국토부 실거래가'} · 정보공개센터
        </span>
      </div>
    </div>
  )
}

export type { GapItem }
