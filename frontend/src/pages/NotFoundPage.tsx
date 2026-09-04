import { AppLink } from '../app/router'

export function NotFoundPage() {
  return <div className="state-card"><p className="eyebrow">404</p><h1>页面不存在</h1><p>这个地址不在第一版 MVP 的开放范围内。</p><AppLink to="/dashboard" className="button primary">返回工作台</AppLink></div>
}
