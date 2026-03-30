import type { AgentMessage } from '../../api/types'

interface Props {
  message: AgentMessage
}

const ROLE_CONFIG: Record<string, { bg: string; border: string; badge: string; badgeText: string; times: string[] }> = {
  suspicion: {
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    badge: 'bg-blue-100 text-blue-700',
    badgeText: '민주당 지지자 AI',
    times: ['23분 전', '5분 전', '1분 전'],
  },
  optimist: {
    bg: 'bg-red-50',
    border: 'border-red-200',
    badge: 'bg-red-100 text-red-700',
    badgeText: '국민의힘 지지자 AI',
    times: ['18분 전', '3분 전', '방금'],
  },
  factcheck: {
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    badge: 'bg-amber-100 text-amber-700',
    badgeText: '중도 농부 AI',
    times: ['12분 전', '2분 전', '방금'],
  },
}

export default function AgentCard({ message }: Props) {
  const config = ROLE_CONFIG[message.role] || ROLE_CONFIG.factcheck
  // confidence 0이면 기본 댓글, 아니면 라이브
  const isDefault = message.confidence === 0 && message.isComplete
  const timeText = isDefault ? config.times[0] : config.times[2]

  return (
    <div className={`rounded-lg border ${config.border} ${config.bg} p-4 mb-3`}>
      {/* Header */}
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xl">{message.emoji}</span>
        <div className="flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-bold text-sm text-slate-800">{message.displayName}</span>
            <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${config.badge}`}>
              {config.badgeText}
            </span>
          </div>
          <span className="text-[11px] text-slate-400">{timeText}</span>
        </div>
        {!isDefault && message.isComplete && (
          <span className="text-[10px] bg-green-100 text-green-600 px-2 py-0.5 rounded-full">AI 분석</span>
        )}
      </div>

      {/* Body */}
      <div className="text-[13px] text-slate-700 leading-relaxed whitespace-pre-wrap pl-7">
        {message.content || (
          <span className="text-slate-300 italic">댓글 작성 중...</span>
        )}
        {!message.isComplete && message.content && (
          <span className="inline-block w-1.5 h-3.5 bg-slate-400 animate-pulse ml-0.5 align-middle rounded-sm" />
        )}
      </div>
    </div>
  )
}
