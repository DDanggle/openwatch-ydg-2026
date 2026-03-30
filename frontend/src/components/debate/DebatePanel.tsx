import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { usePoliticianDetail } from '../../hooks/usePoliticianDetail'
import { useDebateStore } from '../../hooks/useDebateStream'
import AgentCard from './AgentCard'
import TopicButtons from './TopicButtons'
import FollowUpChips from './FollowUpChips'
import DisclaimerFooter from './DisclaimerFooter'
import type { AgentMessage } from '../../api/types'

function makeDefaultComments(name: string, party: string | null): AgentMessage[] {
  const isRight = (party || '').includes('국민의힘')

  return [
    {
      role: 'suspicion',
      displayName: '파란장미',
      emoji: '🌹',
      isComplete: true,
      confidence: 0,
      content: isRight
        ? `${name} 의원 재산 기사 보고 왔는데... 와 진짜 어떻게 국회의원 하면서 이렇게 모을 수 있는 건지 ㅋㅋ 부동산이 대부분이라던데 타이밍이 기가 막히네요. 자세한 분석 토픽 눌러서 같이 봐요!\n\n👍 128 👎 15`
        : `우리 ${name} 의원님 재산 좀 있긴 한데... 솔직히 의정활동은 잘 하시잖아요. 근데 가족 명의가 좀 많다는 얘기는 있더라구요. 한번 파봐야겠어요\n\n👍 95 👎 32`,
    },
    {
      role: 'optimist',
      displayName: '태극기전사',
      emoji: '🇰🇷',
      isComplete: true,
      confidence: 0,
      content: isRight
        ? `${name} 의원은 원래 사업가 출신이에요! 재산 많은 게 당연한 거지! 능력 있는 분이 국회 가서 경제 살려야죠!! 괜히 트집 잡지 맙시다!\n\n👍 87 👎 41`
        : `${name} 의원 재산 엄청 많다면서요?! 국민 세금으로 배 불린 거 아닙니까?! 이런 분들이 서민 경제 운운하면 안 되지!!\n\n👍 156 👎 23`,
    },
    {
      role: 'factcheck',
      displayName: '논두렁회계사',
      emoji: '🌾',
      isComplete: true,
      confidence: 0,
      content: `허허, 또 시작이여~ ${name} 의원 재산 궁금하면 아래 토픽 버튼 눌러보세유. 제가 숫자로 정리해드릴게유. 정당 가지고 싸우지 말고 팩트를 봐야쥬~\n\n※ 공개 신고자료 기반이니 참고만 하세유~\n\n👍 203 👎 4`,
    },
  ]
}

export default function DebatePanel() {
  const { id } = useParams<{ id: string }>()
  const { data: pol } = usePoliticianDetail(id || '')
  const { messages, isStreaming, followupQuestions, disclaimer, startDebate, sendFollowup, reset } =
    useDebateStore()

  const [defaultComments, setDefaultComments] = useState<AgentMessage[]>([])

  useEffect(() => {
    if (pol) {
      setDefaultComments(makeDefaultComments(pol.name, pol.party))
    }
    return () => reset()
  }, [pol, reset])

  const handleTopicSelect = (topic: string) => {
    if (id) startDebate(id, topic)
  }

  const handleFollowup = (question: string) => {
    if (id) sendFollowup(id, question)
  }

  const hasLiveContent = Object.values(messages).some((m) => m.content.length > 0)

  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold text-slate-800 mb-1">
        {pol ? `${pol.name} 의원` : ''} 시민 댓글 토론
      </h1>
      <p className="text-sm text-slate-500 mb-6">
        3명의 AI 에이전트가 각자의 정치 성향으로 댓글을 남깁니다. 실제 인물이 아닌 AI가 생성한 캐릭터입니다.
      </p>

      {/* 댓글 영역 — 기본 + 라이브 모두 한 덩어리 */}
      <div className="bg-white rounded-lg border border-slate-200 p-4 mb-6">
        <div className="flex items-center gap-2 mb-4 pb-3 border-b border-slate-100">
          <span className="text-sm font-semibold text-slate-600">댓글</span>
          <span className="text-xs text-slate-400">
            {defaultComments.length + (hasLiveContent ? 3 : 0)}개
          </span>
          <span className="text-xs text-slate-300 ml-auto">최신순</span>
        </div>

        {/* 기본 댓글 — 항상 보임 */}
        {defaultComments.map((msg, i) => (
          <AgentCard key={`default-${i}`} message={msg} />
        ))}

        {/* 라이브 댓글 — 토픽 선택 후 기본 댓글 밑에 추가 */}
        {hasLiveContent && (
          <>
            <div className="flex items-center gap-2 my-4 pt-3 border-t border-slate-200">
              <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">LIVE</span>
              <span className="text-xs text-slate-400">AI 심층 분석 댓글</span>
            </div>
            <AgentCard message={messages.suspicion} />
            <AgentCard message={messages.optimist} />
            <AgentCard message={messages.factcheck} />
          </>
        )}

        {/* 스트리밍 로딩 */}
        {isStreaming && !hasLiveContent && (
          <div className="text-center py-4 text-sm text-slate-400 animate-pulse">
            AI 에이전트들이 데이터를 분석하고 댓글을 작성하고 있습니다...
          </div>
        )}
      </div>

      {/* 토픽 버튼 — 댓글 아래 */}
      <div className="bg-white rounded-lg border border-slate-200 p-4 mb-6">
        <p className="text-sm font-semibold text-slate-600 mb-3">
          더 자세히 분석해보기
        </p>
        <TopicButtons onSelect={handleTopicSelect} disabled={isStreaming} />
      </div>

      {/* 후속 질문 */}
      {followupQuestions.length > 0 && (
        <FollowUpChips questions={followupQuestions} onSelect={handleFollowup} disabled={isStreaming} />
      )}

      {/* 면책조항 */}
      <DisclaimerFooter text="이 댓글은 AI 에이전트가 공개 데이터를 바탕으로 생성한 것입니다. 실제 인물의 의견이 아닙니다." />
    </div>
  )
}
