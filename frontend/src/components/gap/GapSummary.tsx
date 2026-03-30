interface Props {
  totalPoliticians: number
  totalMatches: number
  avgGapPct: number
  maxGapPct: number
}

export default function GapSummary({ totalPoliticians, totalMatches, avgGapPct, maxGapPct }: Props) {
  return (
    <div className="mb-10">
      {/* Headline */}
      <h1 className="text-3xl font-black text-slate-900 tracking-tight mb-2">
        신고가 vs 실거래가
      </h1>
      <p className="text-lg text-slate-500 mb-6 max-w-2xl leading-relaxed">
        국회의원이 신고한 아파트 가액과 최근 실거래가를 비교합니다.
        평균 <span className="font-bold text-red-600">+{avgGapPct.toFixed(0)}%</span> 저평가되어 있습니다.
      </p>

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="분석 대상" value={`${totalPoliticians}명`} sub="국회의원·고위공직자" />
        <StatCard label="매칭 건수" value={`${totalMatches}건`} sub="아파트명+면적 exact/fuzzy" />
        <StatCard label="평균 괴리율" value={`+${avgGapPct.toFixed(0)}%`} sub="신고가(공시) 대비" color="text-red-600" />
        <StatCard label="공시가 현실화율" value="약 62%" sub="검증 5건 평균 기준" color="text-slate-600" />
      </div>

      {/* Methodology note */}
      <div className="mt-4 p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-500 leading-relaxed">
        <span className="font-semibold text-slate-600">분석 방법: </span>
        2026 정기재산변동신고의 아파트 신고가(공시가격 기준)와 국토부 실거래가 공개시스템의 2025.01~03 거래 데이터를
        아파트명+면적으로 자동 매칭합니다. 공유지분(A㎡중 B㎡)은 실거래가에 지분비율을 적용하여 보정합니다.
        재산신고는 공시가격 기준이므로, 실거래가와의 차이(약 30~70%)는 <span className="font-semibold">제도적 특성</span>입니다.
        이 중 평균보다 현저히 높은 괴리는 추가 확인이 필요할 수 있습니다.
      </div>
    </div>
  )
}

function StatCard({ label, value, sub, color }: { label: string; value: string; sub: string; color?: string }) {
  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4">
      <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">{label}</div>
      <div className={`text-2xl font-black mt-1 ${color || 'text-slate-800'}`}>{value}</div>
      <div className="text-xs text-slate-400 mt-0.5">{sub}</div>
    </div>
  )
}
