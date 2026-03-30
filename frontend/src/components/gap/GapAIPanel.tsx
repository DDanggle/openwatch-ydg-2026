import { useState, useEffect } from 'react'
import { formatWon } from '../../lib/formatters'
import type { GapItem } from './GapCard'
import type { AgentMessage, AgentRole } from '../../api/types'

const API = 'http://localhost:8010/api'

interface Props {
  item: GapItem
  onClose: () => void
}

const AGENTS: Record<AgentRole, { name: string; emoji: string; badge: string; bg: string; border: string }> = {
  suspicion: { name: '파란장미', emoji: '🌹', badge: '민주당 지지자 AI', bg: 'bg-blue-50', border: 'border-blue-200' },
  optimist: { name: '태극기전사', emoji: '🇰🇷', badge: '국민의힘 지지자 AI', bg: 'bg-red-50', border: 'border-red-200' },
  factcheck: { name: '논두렁회계사', emoji: '🌾', badge: '중도 농부 AI', bg: 'bg-amber-50', border: 'border-amber-200' },
}

function buildMockComments(item: GapItem): Record<AgentRole, string> {
  const d = formatWon(item.declared_value)
  const e = formatWon(item.estimated_value)
  const pct = item.gap_pct.toFixed(0)
  const name = item.politician_name
  const apt = item.apartment_name || '해당 부동산'
  const loc = item.location

  return {
    suspicion: `${name} ${apt} 신고가 ${d}인데 실거래가 기준 ${e}라구요?? +${pct}% 차이면 ㅋㅋ 이건 좀 설명이 필요한 거 아닌가요? ${loc}에 이 가격이면 주변 시세 생각해봐도 너무 낮게 신고한 거 아닌지... 공시가격 기준이라고 해도 이 정도 차이는 좀 의아합니다\n\n👍 234 👎 31`,
    optimist: `재산신고는 공시가격 기준이에요! ${apt}의 공시가격과 실거래가는 원래 차이가 큰 겁니다! 2025년 공시가격 현실화율이 60~70% 수준인데 +${pct}%면 오히려 정상 범위 아닙니까!! ${name} 의원이 뭘 잘못한 건 아니에요!\n\n👍 187 👎 52`,
    factcheck: `숫자로 보자면여...\n\n• ${apt} (${loc})\n• 신고가: ${d} (공시가격 기준)\n• 실거래 추정: ${e} (2025.01~03 거래 기준)\n• 차이: +${pct}%\n• 매칭 신뢰도: ${(item.match_confidence * 100).toFixed(0)}%\n\n공시가격 현실화율(전국 평균 약 69%)을 감안하면 30~50% 차이는 제도적 요인이여. 다만 그 이상은 추가 확인이 필요할 수 있어유.\n\n※ 국토부 실거래가 공개시스템 + 정보공개센터 자료 기반 추정\n\n👍 312 👎 8`,
  }
}

export default function GapAIPanel({ item, onClose }: Props) {
  const [comments, setComments] = useState<Record<AgentRole, string> | null>(null)
  const [streaming, setStreaming] = useState(false)

  useEffect(() => {
    // 즉시 목 댓글 표시 (나중에 실제 AI 호출로 교체 가능)
    setComments(buildMockComments(item))
  }, [item])

  if (!comments) return null

  return (
    <div className="bg-white border-2 border-indigo-200 rounded-xl p-5 mb-6 shadow-lg">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-base font-bold text-slate-800">
            AI 분석: {item.apartment_name || '부동산'} 괴리 토론
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            {item.politician_name} · {item.location} · 괴리율 +{item.gap_pct.toFixed(0)}%
          </p>
        </div>
        <button
          onClick={onClose}
          className="text-slate-400 hover:text-slate-600 text-xl leading-none px-2"
        >
          &times;
        </button>
      </div>

      {/* Agent comments */}
      <div className="space-y-3">
        {(Object.keys(AGENTS) as AgentRole[]).map((role) => {
          const agent = AGENTS[role]
          return (
            <div key={role} className={`rounded-lg border ${agent.border} ${agent.bg} p-3`}>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-lg">{agent.emoji}</span>
                <span className="font-bold text-xs text-slate-700">{agent.name}</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-white/60 text-slate-500">
                  {agent.badge}
                </span>
              </div>
              <p className="text-xs text-slate-700 leading-relaxed whitespace-pre-wrap pl-7">
                {comments[role]}
              </p>
            </div>
          )
        })}
      </div>

      <div className="mt-3 text-[10px] text-slate-300 text-center">
        AI 에이전트가 생성한 캐릭터 댓글입니다. 실제 인물의 의견이 아닙니다.
      </div>
    </div>
  )
}
