import { useState } from 'react'
import { useGrowthRanking, useFamilyRanking, useGapRanking } from '../../hooks/useLeaderboard'
import LeaderboardTable from './LeaderboardTable'

const TABS = [
  { key: 'growth', label: '성장률 TOP', desc: '종전가액 대비 현재가액 증가율이 높은 의원' },
  { key: 'family', label: '가족 기여도 TOP', desc: '전체 자산 중 가족(배우자·자녀 등) 명의 비중이 높은 의원' },
  { key: 'gap', label: '부동산 괴리 TOP', desc: '아파트 신고가 대비 실거래 추정가 괴리가 큰 의원' },
] as const

type TabKey = typeof TABS[number]['key']

export default function LeaderboardPage() {
  const [activeTab, setActiveTab] = useState<TabKey>('growth')

  const growth = useGrowthRanking(30)
  const family = useFamilyRanking(30)
  const gap = useGapRanking(30)

  const dataMap = { growth, family, gap }
  const current = dataMap[activeTab]
  const currentTab = TABS.find(t => t.key === activeTab)!

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-800 mb-1">국회의원 재산 랭킹</h1>
      <p className="text-sm text-slate-500 mb-4">2026 정기재산변동신고 기준 · 정보공개센터 (CC BY-SA 4.0)</p>

      {/* Tabs */}
      <div className="flex gap-1 mb-2 bg-slate-100 rounded-lg p-1 w-fit">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              activeTab === tab.key
                ? 'bg-white text-slate-800 shadow-sm'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <p className="text-xs text-slate-400 mb-4">{currentTab.desc}</p>

      {/* Table */}
      {current.isLoading && <div className="text-center py-12 text-slate-400">로딩 중...</div>}
      {current.error && <div className="text-center py-12 text-red-500">데이터를 불러오지 못했습니다.</div>}
      {current.data && (
        <LeaderboardTable items={current.data.items} rankingType={current.data.ranking_type} />
      )}

      <div className="mt-4 text-xs text-slate-400">
        성장률 = (현재가액 - 종전가액) / 종전가액 × 100 | 가족 기여도 = 가족 명의 자산 / 전체 자산 × 100
      </div>
    </div>
  )
}
