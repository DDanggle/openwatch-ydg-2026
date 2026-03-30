import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import type { TimelinePoint } from '../../api/types'

interface Props {
  timeline: TimelinePoint[]
}

const COLORS = ['#3b82f6', '#f59e0b', '#10b981']

export default function FamilyPieChart({ timeline }: Props) {
  if (timeline.length === 0) {
    return <div className="text-center py-8 text-slate-400">데이터 없음</div>
  }

  const latest = timeline[timeline.length - 1]
  const familyOther = Math.max(0, latest.family_amount - latest.spouse_amount)

  const data = [
    { name: '본인', value: latest.self_amount },
    { name: '배우자', value: latest.spouse_amount },
    { name: '기타 가족', value: familyOther },
  ].filter((d) => d.value > 0)

  const total = data.reduce((s, d) => s + d.value, 0)

  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={100}
          dataKey="value"
          label={({ name, value }) =>
            `${name} ${total > 0 ? ((value / total) * 100).toFixed(0) : 0}%`
          }
        >
          {data.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip
          formatter={(value) => {
            const eok = Number(value) / 100_000_000
            return [`${eok.toFixed(1)}억원`]
          }}
        />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  )
}
