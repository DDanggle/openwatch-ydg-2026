import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { formatWon } from '../../lib/formatters'

const DATA_BASE = '/data'

interface Dot {
  id: number; name: string; apt: string; sido: string; sigungu: string; dong: string
  gap: number; method: string; confidence: number; area: number
  declared: number; estimated: number; party: string
  detail: string; relation: string; trade_date: string; share_ratio: number
  family_total?: { members: { relation: string; declared: number }[]; total_declared: number } | null
}
interface Region { sido: string; count: number; avg_gap: number; min_gap: number; max_gap: number; excess_count: number }
interface Portfolio {
  name: string; position: string; party: string; politician_id: string
  asset_count: number; total_declared: number; total_estimated: number
  avg_gap: number; max_gap: number; apartments: string; sidos: string
}
interface DistData {
  stats: {
    total: number; mean: number; median: number; q1: number; q3: number
    expected_band: [number, number]; excess_count: number
    high_confidence_count: number; high_confidence_pct: number
  }
  dots: Dot[]; regions: Region[]; portfolios: Portfolio[]
}

function useDistribution() {
  return useQuery<DistData>({
    queryKey: ['gap-dist'],
    queryFn: async () => { const r = await fetch(`${DATA_BASE}/gap_distribution.json`); return r.json() },
  })
}

const PARTY_COLORS: Record<string, string> = {
  '국민의힘': '#E02D2D', '더불어민주당': '#1B56FD', '조국혁신당': '#0D47A1', '기타': '#9E9E9E', '국회': '#6B7280',
}
const partyColor = (p: string) => PARTY_COLORS[p] || '#6B7280'
const toPlat = (sqm: number) => sqm ? `${(sqm / 3.306).toFixed(0)}평` : ''
const naverLink = (q: string) => `https://search.naver.com/search.naver?query=${encodeURIComponent(q + ' 아파트 시세')}`

const METHOD_KR: Record<string, string> = {
  'exact': '정확 매칭 (아파트명+면적 일치)',
  'fuzzy_name': '유사 매칭 (아파트명 유사+면적 근접)',
  'dong_area': '지역 매칭 (동+면적 기준)',
  'manual_api_search': '수동 검색 (API 평균가 기준)',
  'manual_csv': '수동 입력',
  'sigungu_avg': '시군구 평균',
}
const methodKr = (m: string) => METHOD_KR[m] || m

const relationLabel = (r: string) => {
  if (r === '본인') return '본인 소유'
  return `가족 소유 (${r} 명의)`
}

// ── 인라인 상세 (행 아래 확장) ──
function InlineDetail({ dot }: { dot: Dot }) {
  const isExcess = dot.gap > 70
  const isNeg = dot.gap < 0
  const shareText = dot.share_ratio && dot.share_ratio < 1 ? `지분 ${(dot.share_ratio * 100).toFixed(0)}%` : null
  const loc = [dot.sido, dot.sigungu, dot.dong].filter(Boolean).join(' ')

  return (
    <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 mt-1 mb-2 text-xs animate-in">
      <div className="grid grid-cols-1 md:grid-cols-[1fr_300px] gap-4">
        {/* 왼쪽: 비교 */}
        <div className="space-y-3">
          {/* 원본 신고 */}
          <div className="p-2.5 bg-white rounded border border-slate-100">
            <div className="text-[10px] text-slate-400 mb-1">원본 신고 내용</div>
            <div className="text-slate-700 leading-relaxed">{dot.detail}</div>
          </div>

          {/* 면적 정보 */}
          <div className="flex flex-wrap gap-3">
            {dot.area > 0 && (
              <div className="px-2.5 py-1.5 bg-white rounded border border-slate-100">
                <span className="text-slate-400">전용면적</span>{' '}
                <span className="font-bold text-slate-700">{dot.area.toFixed(1)}㎡</span>{' '}
                <span className="text-slate-400">({toPlat(dot.area)})</span>
              </div>
            )}
            {shareText && (
              <div className="px-2.5 py-1.5 bg-purple-50 rounded border border-purple-100">
                <span className="text-purple-500">공유지분</span>{' '}
                <span className="font-bold text-purple-700">{shareText}</span>{' '}
                <span className="text-purple-400">(실거래가 × 지분비율로 보정)</span>
              </div>
            )}
            <div className={`px-2.5 py-1.5 rounded border ${dot.relation === '본인' ? 'bg-white border-slate-100' : 'bg-orange-50 border-orange-100'}`}>
              <span className={dot.relation === '본인' ? 'text-slate-400' : 'text-orange-500'}>소유</span>{' '}
              <span className={`font-bold ${dot.relation === '본인' ? 'text-slate-700' : 'text-orange-700'}`}>{relationLabel(dot.relation)}</span>
            </div>
          </div>

          {/* 가족 합산 */}
          {dot.family_total && (
            <div className="p-2.5 bg-orange-50 rounded border border-orange-100">
              <div className="text-[10px] text-orange-500 mb-1">같은 아파트 가족 명의 합산</div>
              <div className="flex flex-wrap gap-2">
                {dot.family_total.members.map((m, i) => (
                  <span key={i} className="text-orange-700">
                    {m.relation}: {formatWon(m.declared)}
                  </span>
                ))}
              </div>
              <div className="text-orange-700 font-bold mt-1">
                합산 신고가: {formatWon(dot.family_total.total_declared)}
              </div>
            </div>
          )}

          {/* 비교 바 */}
          <div className="space-y-2">
            <div>
              <div className="flex justify-between mb-0.5">
                <span className="text-slate-500">신고가 <span className="text-slate-300">(2026 공시가격)</span></span>
                <span className="font-bold text-slate-700">{formatWon(dot.declared)}</span>
              </div>
              <div className="h-6 bg-slate-100 rounded-full overflow-hidden">
                <div className="h-full bg-slate-400 rounded-full transition-all duration-500"
                  style={{ width: `${dot.declared / Math.max(dot.declared, dot.estimated) * 100}%` }} />
              </div>
            </div>
            <div>
              <div className="flex justify-between mb-0.5">
                <span className="text-blue-600">실거래 추정 <span className="text-slate-300">({dot.trade_date || '2024~2025'})</span></span>
                <span className="font-bold text-blue-600">{formatWon(dot.estimated)}</span>
              </div>
              <div className="h-6 bg-blue-50 rounded-full overflow-hidden">
                <div className="h-full bg-blue-500 rounded-full transition-all duration-500"
                  style={{ width: `${dot.estimated / Math.max(dot.declared, dot.estimated) * 100}%` }} />
              </div>
            </div>
          </div>

          {/* 괴리 */}
          <div className={`text-center py-2 rounded-lg ${isExcess ? 'bg-red-50' : isNeg ? 'bg-green-50' : 'bg-amber-50'}`}>
            <span className="text-slate-500 mr-2">괴리</span>
            <span className={`text-lg font-black ${isExcess ? 'text-red-600' : isNeg ? 'text-green-600' : 'text-amber-600'}`}>
              {dot.gap > 0 ? '+' : ''}{formatWon(dot.estimated - dot.declared)} ({dot.gap > 0 ? '+' : ''}{dot.gap}%)
            </span>
            {isExcess && <span className="text-red-400 text-[10px] ml-2">예상 구간 초과</span>}
            {isNeg && <span className="text-green-400 text-[10px] ml-2">신고가가 더 높음 — 확인 필요</span>}
          </div>
        </div>

        {/* 오른쪽: 메타 + 링크 */}
        <div className="space-y-3">
          <div className="p-3 bg-white rounded-lg border border-slate-100 space-y-1.5">
            <div className="font-semibold text-slate-600 mb-1">비교 방법</div>
            <div className="flex justify-between"><span className="text-slate-400">매칭 방식</span><span className="text-right max-w-[180px]">{methodKr(dot.method)}</span></div>
            <div className="flex justify-between"><span className="text-slate-400">매칭 신뢰도</span><span>{(dot.confidence * 100).toFixed(0)}%</span></div>
            <div className="flex justify-between"><span className="text-slate-400">실거래 기준일</span><span>{dot.trade_date || '2024~2025'}</span></div>
            <div className="flex justify-between"><span className="text-slate-400">부동산 위치</span><span>{loc}</span></div>
          </div>

          <div className="space-y-1.5">
            <div className="font-semibold text-slate-600">출처 확인</div>
            <a href={naverLink(dot.apt || loc)} target="_blank" rel="noreferrer"
              className="flex items-center gap-2 px-3 py-2 bg-green-50 border border-green-200 rounded-lg text-green-700 hover:bg-green-100">
              <span className="text-base">🏠</span>
              <div>
                <div className="font-medium">네이버 부동산</div>
                <div className="text-[10px] text-green-500">"{dot.apt || loc}" 시세 확인</div>
              </div>
              <span className="ml-auto">↗</span>
            </a>
            <a href="https://rt.molit.go.kr" target="_blank" rel="noreferrer"
              className="flex items-center gap-2 px-3 py-2 bg-blue-50 border border-blue-200 rounded-lg text-blue-700 hover:bg-blue-100">
              <span className="text-base">📊</span>
              <div>
                <div className="font-medium">국토부 실거래가</div>
                <div className="text-[10px] text-blue-500">공식 실거래 데이터</div>
              </div>
              <span className="ml-auto">↗</span>
            </a>
          </div>

          <div className="text-[10px] text-slate-300 leading-relaxed">
            신고가: 정보공개센터 2026 정기재산변동신고 (CC BY-SA 4.0)<br/>
            실거래: 국토부 실거래가 공개시스템 (data.go.kr)
          </div>
        </div>
      </div>
    </div>
  )
}

// ── 분포 차트 ──
function DistributionChart({ dots, stats, selectedId, onDotClick }: { dots: Dot[]; stats: DistData['stats']; selectedId: number | null; onDotClick: (d: Dot) => void }) {
  const W = 800, H = 200, PAD = 60
  const minG = Math.min(-80, ...dots.map(d => d.gap))
  const maxG = Math.max(250, ...dots.map(d => d.gap))
  const scale = (v: number) => PAD + ((v - minG) / (maxG - minG)) * (W - PAD * 2)
  const [bandL, bandR] = stats.expected_band
  const jitteredDots = dots.map((d, i) => ({
    ...d, cx: scale(d.gap), cy: 70 + (Math.sin(i * 3.7) * 40) + (Math.cos(i * 2.3) * 20),
  }))
  const [hovered, setHovered] = useState<Dot | null>(null)

  return (
    <div className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxHeight: 220 }}>
        <rect x={scale(bandL)} y={20} width={scale(bandR) - scale(bandL)} height={H - 50} fill="#f1f5f9" stroke="#cbd5e1" strokeDasharray="4 2" rx={4} />
        <text x={scale((bandL + bandR) / 2)} y={16} textAnchor="middle" className="fill-slate-400" style={{ fontSize: 9 }}>예상 구간 (+{bandL}~{bandR}%)</text>
        <line x1={scale(0)} y1={20} x2={scale(0)} y2={H - 25} stroke="#94a3b8" strokeWidth={1} />
        <line x1={scale(stats.median)} y1={25} x2={scale(stats.median)} y2={H - 30} stroke="#ef4444" strokeWidth={1.5} strokeDasharray="6 3" />
        <text x={scale(stats.median)} y={H - 12} textAnchor="middle" style={{ fontSize: 9, fontWeight: 700 }} className="fill-red-500">중앙값 +{stats.median}%</text>
        {jitteredDots.map((d) => (
          <circle key={d.id} cx={d.cx} cy={d.cy}
            r={selectedId === d.id ? 8 : d.confidence >= 0.7 ? 5 : 3.5}
            fill={d.gap > bandR ? '#ef4444' : d.gap > bandL ? '#f59e0b' : d.gap > 0 ? '#94a3b8' : '#22c55e'}
            opacity={selectedId === d.id ? 1 : d.confidence >= 0.7 ? 0.8 : 0.4}
            stroke={selectedId === d.id ? '#000' : d.method === 'exact' ? '#1e293b' : 'none'}
            strokeWidth={selectedId === d.id ? 2 : 1.5}
            onMouseEnter={() => setHovered(d)} onMouseLeave={() => setHovered(null)}
            onClick={() => onDotClick(d)} className="cursor-pointer" />
        ))}
        {[-50, 0, 50, 100, 150, 200].map(v => (
          <text key={v} x={scale(v)} y={H - 3} textAnchor="middle" style={{ fontSize: 8 }} className="fill-slate-300">{v > 0 ? '+' : ''}{v}%</text>
        ))}
      </svg>
      {hovered && (
        <div className="absolute top-0 right-0 bg-white border border-slate-200 rounded-lg p-3 shadow-lg text-xs max-w-[280px] z-10 pointer-events-none">
          <div className="font-bold">{hovered.name} <span style={{ color: partyColor(hovered.party) }}>({hovered.party})</span></div>
          <div className="text-slate-500">{hovered.apt} · {hovered.sido} · {hovered.area > 0 ? `${hovered.area.toFixed(0)}㎡(${toPlat(hovered.area)})` : ''}</div>
          <div className="mt-1">신고 {formatWon(hovered.declared)} → 추정 {formatWon(hovered.estimated)}</div>
          <div className={`font-bold ${hovered.gap > 70 ? 'text-red-600' : 'text-slate-600'}`}>{hovered.gap > 0 ? '+' : ''}{hovered.gap}%</div>
          <div className="text-slate-300 mt-1">클릭하면 상세</div>
        </div>
      )}
      <div className="flex flex-wrap gap-3 mt-2 text-[10px] text-slate-500">
        <span><span className="inline-block w-2.5 h-2.5 rounded-full bg-red-500 mr-1" />예상 초과</span>
        <span><span className="inline-block w-2.5 h-2.5 rounded-full bg-amber-500 mr-1" />예상 구간</span>
        <span><span className="inline-block w-2.5 h-2.5 rounded-full bg-slate-400 mr-1" />제도적</span>
        <span><span className="inline-block w-2.5 h-2.5 rounded-full bg-green-500 mr-1" />음수</span>
        <span><span className="inline-block w-2.5 h-2.5 rounded-full border-2 border-slate-800 mr-1" />exact</span>
      </div>
    </div>
  )
}

// ── 시도 타일맵 ──
function RegionTileMap({ regions, onSelect, selected }: { regions: Region[]; onSelect: (s: string | null) => void; selected: string | null }) {
  const TILES: Record<string, [number, number]> = {
    '서울': [3, 1], '인천': [2, 1], '경기': [3, 0], '강원': [4, 0],
    '세종': [2, 2], '대전': [3, 2], '충북': [4, 1], '충남': [2, 3],
    '전북': [3, 3], '대구': [5, 2], '경북': [5, 1], '광주': [2, 4],
    '전남': [3, 4], '경남': [5, 3], '부산': [5, 4], '울산': [6, 3], '제주': [3, 5],
  }
  const regionMap = Object.fromEntries(regions.map(r => [r.sido, r]))
  return (
    <svg viewBox="0 0 420 360" className="w-full" style={{ maxWidth: 400 }}>
      {Object.entries(TILES).map(([name, [col, row]]) => {
        const r = regionMap[name]
        const x = col * 58 + 10, y = row * 58 + 10
        const avgGap = r?.avg_gap || 0
        const fill = !r ? '#f8fafc' : avgGap > 70 ? '#fecaca' : avgGap > 40 ? '#fef3c7' : avgGap > 0 ? '#e2e8f0' : '#d1fae5'
        return (
          <g key={name} onClick={() => onSelect(selected === name ? null : name)} className="cursor-pointer">
            <rect x={x} y={y} width={52} height={52} rx={6} fill={fill}
              stroke={selected === name ? '#1e293b' : '#cbd5e1'} strokeWidth={selected === name ? 2.5 : 1} />
            <text x={x + 26} y={y + 18} textAnchor="middle" style={{ fontSize: 11, fontWeight: 700 }} className="fill-slate-700">{name}</text>
            {r && <>
              <text x={x + 26} y={y + 32} textAnchor="middle" style={{ fontSize: 9 }} className="fill-slate-500">+{r.avg_gap}%</text>
              <text x={x + 26} y={y + 44} textAnchor="middle" style={{ fontSize: 8 }} className="fill-slate-400">{r.count}건</text>
            </>}
          </g>
        )
      })}
    </svg>
  )
}

// ── 덤벨 행 + 확장 상세 ──
function AssetRow({ d, isOpen, onToggle }: { d: Dot; isOpen: boolean; onToggle: () => void }) {
  const maxScale = 100
  const scale = (v: number) => Math.min((v / 200_0000_0000) * 100, maxScale) // 200억 기준
  const left = Math.min(scale(d.declared), scale(d.estimated))
  const right = Math.max(scale(d.declared), scale(d.estimated))

  return (
    <>
      <div onClick={onToggle}
        className={`flex items-center gap-1.5 py-2 px-2 text-xs cursor-pointer rounded transition ${isOpen ? 'bg-slate-100' : 'hover:bg-slate-50'} border-b border-slate-50`}>
        <span className="w-1 h-4 rounded-full shrink-0" style={{ backgroundColor: partyColor(d.party) }} />
        <div className="w-16 shrink-0 truncate font-medium text-slate-700">{d.name}</div>
        <div className="w-24 shrink-0 truncate text-slate-400" title={d.apt}>{d.apt || '-'}</div>
        <div className="w-14 shrink-0 text-slate-400 text-right">{d.area > 0 ? `${d.area.toFixed(0)}㎡` : '-'}</div>
        <div className="w-10 shrink-0 text-slate-300 text-right">{toPlat(d.area)}</div>
        <div className="flex-1 h-4 relative bg-slate-50 rounded-full mx-1">
          <div className="absolute top-1/2 h-px bg-slate-300" style={{ left: `${left}%`, width: `${right - left}%` }} />
          <div className="absolute top-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-slate-400" style={{ left: `${scale(d.declared)}%` }} />
          <div className={`absolute top-1/2 -translate-y-1/2 w-2 h-2 rounded-full ${d.gap > 70 ? 'bg-red-500' : 'bg-blue-500'}`} style={{ left: `${scale(d.estimated)}%` }} />
        </div>
        <div className="w-14 text-right shrink-0 text-slate-500">{formatWon(d.declared)}</div>
        <div className="w-14 text-right shrink-0 text-blue-600 font-medium">{formatWon(d.estimated)}</div>
        <div className={`w-12 text-right shrink-0 font-bold ${d.gap > 70 ? 'text-red-600' : d.gap > 0 ? 'text-slate-600' : 'text-green-600'}`}>
          {d.gap > 0 ? '+' : ''}{d.gap}%
        </div>
        <span className="text-slate-300 shrink-0 w-4 text-center">{isOpen ? '▲' : '▼'}</span>
      </div>
      {isOpen && <InlineDetail dot={d} />}
    </>
  )
}

// ── 메인 페이지 ──
export default function GapPage() {
  const { data, isLoading, error } = useDistribution()
  const [view, setView] = useState<'asset' | 'politician'>('asset')
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [selectedRegion, setSelectedRegion] = useState<string | null>(null)
  const [assetSort, setAssetSort] = useState<'value' | 'gap'>('value')

  if (isLoading) return <div className="max-w-5xl mx-auto py-16 text-center text-slate-400">데이터 로딩...</div>
  if (error || !data) return <div className="max-w-5xl mx-auto py-16 text-center text-red-500">로드 실패</div>

  const { stats, dots, regions, portfolios } = data

  const handleDotClick = (d: Dot) => {
    setSelectedId(selectedId === d.id ? null : d.id)
  }

  // 지역 필터 적용
  const filteredDots = selectedRegion ? dots.filter(d => d.sido === selectedRegion) : dots
  const filteredSortedDots = [...filteredDots].sort((a, b) => assetSort === 'gap' ? b.gap - a.gap : b.declared - a.declared)
  const filteredPortfolios = selectedRegion
    ? portfolios.filter(p => p.sidos?.includes(selectedRegion))
    : portfolios

  return (
    <div className="max-w-5xl mx-auto">
      <h1 className="text-3xl font-black text-slate-900 tracking-tight mb-1">신고가 vs 실거래가: 구조적 괴리 분석</h1>
      <p className="text-sm text-slate-500 mb-6 max-w-3xl">
        점이나 행을 클릭하면 면적(㎡/평), 신고 원본, 실거래 기준일, 출처 링크를 확인할 수 있습니다.
      </p>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-8">
        <StatBox label="분석 대상" value={`${stats.total}건`} />
        <StatBox label="중앙값 괴리" value={`+${stats.median}%`} color="text-slate-700" />
        <StatBox label="예상 초과" value={`${stats.excess_count}건`} color="text-red-600" sub={`전체의 ${(stats.excess_count / stats.total * 100).toFixed(0)}%`} />
        <StatBox label="고신뢰 매칭" value={`${stats.high_confidence_pct}%`} color="text-blue-600" />
        <StatBox label="예상 구간" value={`+${stats.expected_band[0]}~${stats.expected_band[1]}%`} sub="공시가 현실화율 기반" />
      </div>

      {/* 분포 */}
      <section className="mb-10">
        <h2 className="text-lg font-bold text-slate-800 mb-1">전체 분포</h2>
        <p className="text-xs text-slate-400 mb-3">점 클릭 → 아래 목록에서 해당 항목이 열립니다</p>
        <div className="bg-white border border-slate-200 rounded-lg p-4">
          <DistributionChart dots={dots} stats={stats} selectedId={selectedId} onDotClick={handleDotClick} />
        </div>
      </section>

      {/* 지역 */}
      <section className="mb-10">
        <h2 className="text-lg font-bold text-slate-800 mb-1">부동산 소유 위치별</h2>
        <p className="text-xs text-slate-400 mb-3">지역 클릭 → 아래 상세 탐색이 해당 지역으로 필터링됩니다</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-white border border-slate-200 rounded-lg p-4">
            <RegionTileMap regions={regions} onSelect={(r) => { setSelectedRegion(r); setView('asset') }} selected={selectedRegion} />
          </div>
          <div className="bg-white border border-slate-200 rounded-lg p-4">
            <div className="text-xs font-semibold text-slate-600 mb-2">시도별 괴리 <span className="text-slate-400">(클릭 → 아래 상세)</span></div>
            {regions.map(r => (
              <div key={r.sido} onClick={() => { setSelectedRegion(selectedRegion === r.sido ? null : r.sido); setView('asset') }}
                className={`flex items-center gap-2 py-1.5 text-xs border-b border-slate-50 cursor-pointer rounded transition ${selectedRegion === r.sido ? 'bg-slate-100 font-bold' : 'hover:bg-slate-50'}`}>
                <span className="w-10 font-medium text-slate-700">{r.sido}</span>
                <div className="flex-1 h-3 bg-slate-100 rounded-full relative">
                  <div className="absolute h-full bg-amber-200 rounded-full"
                    style={{ left: `${Math.max(0, r.min_gap + 80) / 3.3}%`, width: `${(r.max_gap - r.min_gap) / 3.3}%` }} />
                  <div className="absolute top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-red-500"
                    style={{ left: `${(r.avg_gap + 80) / 3.3}%` }} />
                </div>
                <span className="w-12 text-right text-slate-500">+{r.avg_gap}%</span>
                <span className="w-8 text-right text-slate-400">{r.count}건</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 상세 */}
      <section className="mb-8" id="detail-section">
        <div className="flex items-center gap-3 mb-4 flex-wrap">
          <h2 className="text-lg font-bold text-slate-800">상세 탐색</h2>

          {/* 지역 필터 표시 */}
          {selectedRegion && (
            <span className="flex items-center gap-1 px-3 py-1 bg-slate-800 text-white rounded-full text-xs font-medium">
              {selectedRegion}
              <button onClick={() => setSelectedRegion(null)} className="ml-1 hover:text-slate-300">✕</button>
            </span>
          )}

          <div className="flex gap-1 bg-slate-100 rounded-lg p-0.5">
            {([['asset', '자산별'], ['politician', '의원별']] as const).map(([k, l]) => (
              <button key={k} onClick={() => setView(k)}
                className={`px-3 py-1 rounded-md text-xs font-medium transition ${view === k ? 'bg-white shadow-sm text-slate-800' : 'text-slate-500'}`}>{l}</button>
            ))}
          </div>
          {view === 'asset' && (
            <div className="flex gap-1 ml-auto text-[10px]">
              <button onClick={() => setAssetSort('value')} className={`px-2 py-0.5 rounded ${assetSort === 'value' ? 'bg-slate-800 text-white' : 'bg-slate-100 text-slate-500'}`}>자산순</button>
              <button onClick={() => setAssetSort('gap')} className={`px-2 py-0.5 rounded ${assetSort === 'gap' ? 'bg-slate-800 text-white' : 'bg-slate-100 text-slate-500'}`}>괴리순</button>
            </div>
          )}
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-3">
          {view === 'asset' && (
            <>
              <div className="flex items-center gap-3 mb-2 text-[10px] text-slate-400 px-2">
                <span className="w-1 shrink-0" />
                <span className="w-16 shrink-0">의원</span>
                <span className="w-24 shrink-0">아파트</span>
                <span className="w-14 shrink-0 text-right">면적</span>
                <span className="w-10 shrink-0 text-right">평</span>
                <span className="flex-1 text-center">← 신고가 · 실거래추정 →</span>
                <span className="w-14 text-right shrink-0">신고</span>
                <span className="w-14 text-right shrink-0">추정</span>
                <span className="w-12 text-right shrink-0">괴리</span>
                <span className="w-4 shrink-0" />
              </div>
              {filteredSortedDots.map(d => (
                <AssetRow key={d.id} d={d} isOpen={selectedId === d.id} onToggle={() => handleDotClick(d)} />
              ))}
              {filteredSortedDots.length === 0 && (
                <div className="text-center py-6 text-xs text-slate-400">해당 지역에 매칭 데이터가 없습니다</div>
              )}
            </>
          )}
          {view === 'politician' && (
            <PortfolioList portfolios={filteredPortfolios} dots={filteredDots} onSelect={handleDotClick} selectedId={selectedId} />
          )}
        </div>
      </section>

      <div className="space-y-3 text-xs text-slate-500 mb-8">
        <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg">
          <span className="font-bold text-slate-600">방법론</span>
          <p className="mt-1">재산신고(공시가격)와 국토부 실거래가 API(2024.04~2025.03)를 아파트명+면적으로 자동 매칭. 공유지분 보정. 예상 구간(+25~70%)은 현실화율 기반.</p>
        </div>
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg text-amber-700">
          <span className="font-bold">출처</span>: 정보공개센터 2026 정기재산변동신고 (CC BY-SA 4.0) · 국토부 실거래가 (data.go.kr)
        </div>
      </div>
    </div>
  )
}

// ── 의원별 포트폴리오 ──
function PortfolioList({ portfolios, dots, onSelect, selectedId }: { portfolios: Portfolio[]; dots: Dot[]; onSelect: (d: Dot) => void; selectedId: number | null }) {
  const [expanded, setExpanded] = useState<string | null>(null)
  const [sortBy, setSortBy] = useState<'name' | 'party' | 'gap' | 'value'>('name')
  const sorted = [...portfolios].sort((a, b) => {
    if (sortBy === 'party') return a.party.localeCompare(b.party) || a.name.localeCompare(b.name)
    if (sortBy === 'gap') return b.avg_gap - a.avg_gap
    if (sortBy === 'value') return b.total_declared - a.total_declared
    return a.name.localeCompare(b.name)
  })
  return (
    <div>
      <div className="flex gap-2 mb-3 text-[10px]">
        {([['name', '이름순'], ['party', '정당별'], ['gap', '괴리순'], ['value', '자산순']] as const).map(([k, l]) => (
          <button key={k} onClick={() => setSortBy(k)}
            className={`px-2 py-0.5 rounded ${sortBy === k ? 'bg-slate-800 text-white' : 'bg-slate-100 text-slate-500'}`}>{l}</button>
        ))}
      </div>
      {sorted.map((p) => {
        const totalGapPct = p.total_declared > 0 ? ((p.total_estimated - p.total_declared) / p.total_declared * 100) : 0
        const isOpen = expanded === p.politician_id
        const memberDots = dots.filter(d => d.name === p.name)
        return (
          <div key={p.politician_id} className="border border-slate-100 rounded-lg overflow-hidden mb-1">
            <div className="flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-slate-50 text-xs"
              onClick={() => setExpanded(isOpen ? null : p.politician_id)}>
              <span className="w-1.5 h-6 rounded-full shrink-0" style={{ backgroundColor: partyColor(p.party) }} />
              <span className="font-bold text-slate-800 w-16 shrink-0">{p.name}</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded-full shrink-0" style={{ backgroundColor: partyColor(p.party) + '20', color: partyColor(p.party) }}>
                {p.party === '국회' ? p.position : p.party}
              </span>
              <span className="text-slate-400 w-6 text-center shrink-0">{p.asset_count}</span>
              <span className="flex-1 text-slate-500 truncate">신고 {formatWon(p.total_declared)} → 추정 {formatWon(p.total_estimated)}</span>
              <span className={`font-bold w-14 text-right shrink-0 ${totalGapPct > 70 ? 'text-red-600' : totalGapPct > 0 ? 'text-slate-600' : 'text-green-600'}`}>
                {totalGapPct > 0 ? '+' : ''}{totalGapPct.toFixed(0)}%
              </span>
              <span className="text-slate-300 shrink-0">{isOpen ? '▲' : '▼'}</span>
            </div>
            {isOpen && (
              <div className="px-2 pb-2 bg-slate-50">
                {memberDots.map(d => (
                  <AssetRow key={d.id} d={d} isOpen={selectedId === d.id} onToggle={() => onSelect(d)} />
                ))}
                <div className="text-[10px] text-slate-400 px-2 pt-1">소유 위치: {p.sidos}</div>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

function StatBox({ label, value, sub, color }: { label: string; value: string; sub?: string; color?: string }) {
  return (
    <div className="bg-white border border-slate-200 rounded-lg px-3 py-2.5">
      <div className="text-[10px] font-medium text-slate-400 uppercase tracking-wider">{label}</div>
      <div className={`text-xl font-black mt-0.5 ${color || 'text-slate-800'}`}>{value}</div>
      {sub && <div className="text-[10px] text-slate-400 mt-0.5">{sub}</div>}
    </div>
  )
}
