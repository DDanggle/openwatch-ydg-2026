interface Props {
  questions: string[]
  onSelect: (question: string) => void
  disabled: boolean
}

export default function FollowUpChips({ questions, onSelect, disabled }: Props) {
  return (
    <div className="mt-6 p-4 bg-slate-50 rounded-lg">
      <h4 className="text-sm font-semibold text-slate-600 mb-2">
        더 알아보기
      </h4>
      <div className="flex flex-wrap gap-2">
        {questions.map((q, i) => (
          <button
            key={i}
            onClick={() => onSelect(q)}
            disabled={disabled}
            className="px-3 py-1.5 text-sm rounded-full bg-white border border-slate-200
                       text-slate-700 hover:bg-slate-100 hover:border-slate-300
                       disabled:opacity-40 transition-colors text-left"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  )
}
