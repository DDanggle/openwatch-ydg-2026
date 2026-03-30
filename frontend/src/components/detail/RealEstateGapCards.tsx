import type { RealEstateGapCard } from '../../api/types'
import { formatWon } from '../../lib/formatters'

interface Props {
  gaps: RealEstateGapCard[]
}

export default function RealEstateGapCards({ gaps }: Props) {
  if (gaps.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-slate-200 p-6 text-center text-slate-400">
        매칭된 부동산 실거래 데이터가 없습니다
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {gaps.map((g, i) => (
        <div key={i} className="bg-white rounded-lg border border-slate-200 p-4">
          <div className="text-sm text-slate-500 mb-2 truncate" title={g.property_description}>
            {g.property_description || '부동산'}
          </div>
          <div className="flex justify-between items-end">
            <div>
              <div className="text-xs text-slate-400">신고가</div>
              <div className="text-lg font-semibold">{formatWon(g.declared_value)}</div>
            </div>
            <div className="text-2xl text-slate-300 px-2">&rarr;</div>
            <div>
              <div className="text-xs text-slate-400">추정 시세</div>
              <div className="text-lg font-semibold text-blue-600">
                {formatWon(g.estimated_market_value)}
              </div>
            </div>
            <div className="text-right">
              <div className="text-xs text-slate-400">괴리</div>
              <div className={`text-lg font-bold ${g.gap_pct > 0 ? 'text-red-600' : 'text-green-600'}`}>
                {g.gap_pct > 0 ? '+' : ''}{g.gap_pct.toFixed(0)}%
              </div>
            </div>
          </div>
          <div className="mt-2 flex gap-2">
            <span className="text-xs px-2 py-0.5 bg-slate-100 rounded">
              신뢰도: {(g.match_confidence * 100).toFixed(0)}%
            </span>
            {g.match_method && (
              <span className="text-xs px-2 py-0.5 bg-slate-100 rounded">
                {g.match_method}
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
