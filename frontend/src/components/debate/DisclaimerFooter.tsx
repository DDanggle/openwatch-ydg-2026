interface Props {
  text: string
}

export default function DisclaimerFooter({ text }: Props) {
  return (
    <div className="mt-6 p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-700">
      {text}
    </div>
  )
}
