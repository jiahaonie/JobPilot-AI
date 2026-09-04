/* eslint-disable react-refresh/only-export-components */
import { useEffect, useState, type MouseEvent, type ReactNode } from 'react'

export function navigate(path: string) {
  window.history.pushState({}, '', path)
  window.dispatchEvent(new PopStateEvent('popstate'))
  window.scrollTo({ top: 0 })
}

export function usePathname() {
  const [pathname, setPathname] = useState(window.location.pathname)
  useEffect(() => {
    const update = () => setPathname(window.location.pathname)
    window.addEventListener('popstate', update)
    return () => window.removeEventListener('popstate', update)
  }, [])
  return pathname
}

interface AppLinkProps {
  to: string
  children: ReactNode
  className?: string
}

export function AppLink({ to, children, className }: AppLinkProps) {
  function handleClick(event: MouseEvent<HTMLAnchorElement>) {
    if (
      event.button === 0 &&
      !event.metaKey &&
      !event.ctrlKey &&
      !event.shiftKey &&
      !event.altKey
    ) {
      event.preventDefault()
      navigate(to)
    }
  }

  return (
    <a href={to} className={className} onClick={handleClick}>
      {children}
    </a>
  )
}

export function routeId(pathname: string): number | null {
  const value = pathname.split('/').filter(Boolean).at(-1)
  if (!value || !/^\d+$/.test(value)) return null
  return Number(value)
}
