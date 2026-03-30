interface Props {
  onSelect: (topic: string) => void
  disabled: boolean
}

const TOPICS = [
  { label: '전체 분석', value: '전체 분석', icon: '🔍' },
  { label: '부동산 의혹', value: '부동산 영향', icon: '🏠' },
  { label: '가족 재산', value: '가족 자산', icon: '👨‍👩‍👧‍👦' },
  { label: '급등 시점', value: '자산 급등 시점 분석', icon: '📈' },
  { label: '증여/상속 시그널', value: '상속 및 증여 시그널', icon: '💰' },
]

export default function TopicButtons({ onSelect, disabled }: Props) {
  return (
    <div>
      <p className="text-xs text-slate-400 mb-2">토픽을 선택하면 AI 에이전트들이 댓글을 달기 시작합니다</p>
      <div className="flex flex-wrap gap-2">
        {TOPICS.map((t) => (
          <button
            key={t.value}
            onClick={() => onSelect(t.value)}
            disabled={disabled}
            className="px-4 py-2 rounded-full text-sm font-medium border border-slate-300
                       text-slate-600 hover:bg-slate-800 hover:text-white hover:border-slate-800
                       disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>
    </div>
  )
}
