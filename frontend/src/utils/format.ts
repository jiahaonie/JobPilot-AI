export function formatDate(value: string | null | undefined, dateOnly = false) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    ...(dateOnly ? {} : { hour: '2-digit', minute: '2-digit' }),
  }).format(date)
}

export function scoreText(score: number | null) {
  return score === null ? '不可评分' : `${Math.round(score)}%`
}
