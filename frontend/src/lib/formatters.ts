/** Format won amount to 억원 display */
export function formatWon(amount: number): string {
  const eok = amount / 100_000_000
  if (Math.abs(eok) >= 1) {
    return `${eok.toFixed(1)}억원`
  }
  const man = amount / 10_000
  if (Math.abs(man) >= 1) {
    return `${man.toFixed(0)}만원`
  }
  return `${amount.toLocaleString()}원`
}

/** Format percentage */
export function formatPct(value: number): string {
  return `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`
}
