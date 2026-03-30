interface Props {
  sidos: string[]
  selectedSido: string | null
  onSidoChange: (sido: string | null) => void
  sortBy: string
  onSortChange: (sort: string) => void
}

const SORT_OPTIONS = [
  { value: 'gap_pct', label: '괴리율 높은순' },
  { value: 'estimated', label: '실거래가 높은순' },
  { value: 'declared', label: '신고가 높은순' },
  { value: 'name', label: '이름순' },
]

export default function GapFilters({ sidos, selectedSido, onSidoChange, sortBy, onSortChange }: Props) {
  return (
    <div className="flex flex-wrap items-center gap-3 mb-6">
      {/* 지역 필터 */}
      <div className="flex flex-wrap gap-1.5">
        <button
          onClick={() => onSidoChange(null)}
          className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
            !selectedSido
              ? 'bg-slate-800 text-white'
              : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
          }`}
        >
          전체
        </button>
        {sidos.map((sido) => (
          <button
            key={sido}
            onClick={() => onSidoChange(sido === selectedSido ? null : sido)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
              selectedSido === sido
                ? 'bg-slate-800 text-white'
                : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
            }`}
          >
            {sido}
          </button>
        ))}
      </div>

      {/* 구분선 */}
      <div className="h-6 w-px bg-slate-200 hidden md:block" />

      {/* 정렬 */}
      <select
        value={sortBy}
        onChange={(e) => onSortChange(e.target.value)}
        className="text-xs bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-slate-600"
      >
        {SORT_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
    </div>
  )
}
