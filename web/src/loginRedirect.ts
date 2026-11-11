type Place = { pathname: string; search: string; hash: string }

const SAME_ORIGIN = 'https://kansei.invalid'

export function loginHref({ pathname, search, hash }: Place): string {
    if (pathname === '/login') return `/login${search}`
    const next = pathname + search + hash
    return next === '/' ? '/login' : `/login?${new URLSearchParams({ next })}`
}

export function authSwitchHref(to: '/login' | '/signup', next: string | null): string {
    return next === null ? to : `${to}?${new URLSearchParams({ next })}`
}

function safeNext(next: string | null): string | null {
    if (!next?.startsWith('/')) return null
    const url = new URL(next, SAME_ORIGIN)
    return url.origin !== SAME_ORIGIN || url.pathname === '/login' ? null : next
}

export function returnTo(next: string | null): string {
    return safeNext(next) ?? '/'
}

export function afterSignup(next: string | null): string {
    return safeNext(next) ?? '/following'
}
