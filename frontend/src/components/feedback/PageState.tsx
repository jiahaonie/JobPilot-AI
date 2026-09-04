export function LoadingState({ label = '正在加载数据…' }: { label?: string }) {
  return (
    <div className="state-card" role="status">
      <span className="spinner" aria-hidden="true" />
      <p>{label}</p>
    </div>
  )
}

export function ErrorState({ error, onRetry }: { error: Error; onRetry?: () => void }) {
  return (
    <div className="state-card error-state" role="alert">
      <strong>暂时无法显示内容</strong>
      <p>{error.message}</p>
      {onRetry && <button onClick={onRetry}>重新加载</button>}
    </div>
  )
}

export function EmptyState({ title, description, action }: {
  title: string
  description: string
  action?: React.ReactNode
}) {
  return (
    <div className="state-card empty-state">
      <strong>{title}</strong>
      <p>{description}</p>
      {action}
    </div>
  )
}

export function InlineMessage({ kind, children }: {
  kind: 'success' | 'error' | 'info'
  children: React.ReactNode
}) {
  return <div className={`inline-message ${kind}`} role={kind === 'error' ? 'alert' : 'status'}>{children}</div>
}
