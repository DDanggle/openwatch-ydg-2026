import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import type { TimelinePoint } from '../../api/types'

interface Props {
  timeline: TimelinePoint[]
}

export default function AssetTimelineChart({ timeline }: Props) {
  const data = timeline.map((t) => ({
    year: t.year,
    순자산: Math.round(t.net_assets / 100_000_000 * 10) / 10,
    총자산: Math.round(t.total_assets / 100_000_000 * 10) / 10,
  }))

  if (data.length === 0) {
    return <div className="text-center py-8 text-slate-400">데이터 없음</div>
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey="year" tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 12 }} unit="억" />
        <Tooltip
          formatter={(value) => [`${value}억원`]}
          labelFormatter={(label) => `${label}년`}
        />
        <Line type="monotone" dataKey="순자산" stroke="#1e40af" strokeWidth={2} dot={{ r: 4 }} />
        <Line type="monotone" dataKey="총자산" stroke="#94a3b8" strokeWidth={1} strokeDasharray="5 5" />
      </LineChart>
    </ResponsiveContainer>
  )
}
