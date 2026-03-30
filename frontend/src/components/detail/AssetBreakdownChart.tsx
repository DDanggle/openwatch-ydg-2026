import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import type { TimelinePoint } from '../../api/types'

interface Props {
  timeline: TimelinePoint[]
}

export default function AssetBreakdownChart({ timeline }: Props) {
  const data = timeline.map((t) => ({
    year: t.year,
    부동산: Math.round(t.real_estate / 100_000_000 * 10) / 10,
    예금: Math.round(t.deposit / 100_000_000 * 10) / 10,
    증권: Math.round(t.securities / 100_000_000 * 10) / 10,
    기타: Math.round(
      Math.max(0, t.total_assets - t.real_estate - t.deposit - t.securities) / 100_000_000 * 10
    ) / 10,
  }))

  if (data.length === 0) {
    return <div className="text-center py-8 text-slate-400">데이터 없음</div>
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey="year" tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 12 }} unit="억" />
        <Tooltip formatter={(value) => [`${value}억원`]} />
        <Area type="monotone" dataKey="부동산" stackId="1" fill="#3b82f6" stroke="#2563eb" />
        <Area type="monotone" dataKey="예금" stackId="1" fill="#10b981" stroke="#059669" />
        <Area type="monotone" dataKey="증권" stackId="1" fill="#f59e0b" stroke="#d97706" />
        <Area type="monotone" dataKey="기타" stackId="1" fill="#94a3b8" stroke="#64748b" />
      </AreaChart>
    </ResponsiveContainer>
  )
}
