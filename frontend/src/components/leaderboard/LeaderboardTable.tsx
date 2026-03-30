import { useNavigate } from 'react-router-dom'
import type { RankedPolitician } from '../../api/types'
import { getPartyColor } from '../../lib/partyColors'
import { formatWon, formatPct } from '../../lib/formatters'

interface Props {
  items: RankedPolitician[]
  rankingType: string
}

export default function LeaderboardTable({ items, rankingType }: Props) {
  const navigate = useNavigate()

  return (
    <div className="bg-white rounded-lg shadow-sm border border-slate-200 overflow-hidden">
      <table className="w-full">
        <thead>
          <tr className="bg-slate-50 border-b border-slate-200">
            <th className="px-3 py-3 text-left text-xs font-medium text-slate-500 uppercase w-10">#</th>
            <th className="px-3 py-3 text-left text-xs font-medium text-slate-500 uppercase">이름</th>
            <th className="px-3 py-3 text-left text-xs font-medium text-slate-500 uppercase">정당</th>
            <th className="px-3 py-3 text-right text-xs font-medium text-slate-500 uppercase">순자산</th>
            <th className="px-3 py-3 text-right text-xs font-medium text-slate-500 uppercase">
              {items[0]?.metric_label || '지표'}
            </th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            const partyDisplay = item.party === '국회' ? (item.constituency || '기타') : (item.party || '기타')
            return (
              <tr
                key={item.politician_id + item.rank}
                onClick={() => navigate(`/politician/${item.politician_id}`)}
                className="border-b border-slate-100 hover:bg-slate-50 cursor-pointer transition-colors"
                style={{ borderLeft: `4px solid ${getPartyColor(item.party)}` }}
              >
                <td className="px-3 py-2.5 text-sm font-medium text-slate-400">{item.rank}</td>
                <td className="px-3 py-2.5 text-sm font-semibold text-slate-800">{item.name}</td>
                <td className="px-3 py-2.5 text-sm">
                  <span
                    className="inline-block px-2 py-0.5 rounded-full text-[10px] font-medium text-white"
                    style={{ backgroundColor: getPartyColor(item.party) }}
                  >
                    {partyDisplay}
                  </span>
                </td>
                <td className="px-3 py-2.5 text-sm text-right text-slate-700">
                  {formatWon(item.total_assets_current)}
                </td>
                <td className="px-3 py-2.5 text-sm text-right font-semibold">
                  <span className={item.metric_value > 0 ? 'text-red-600' : 'text-blue-600'}>
                    {formatPct(item.metric_value)}
                  </span>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      {items.length === 0 && (
        <div className="text-center py-8 text-slate-400">데이터가 없습니다</div>
      )}
    </div>
  )
}
