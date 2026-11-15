export type Place = { pathname: string; search: string; hash: string }

const SAME_ORIGIN = 'https://kansei.invalid'

export function loginHref(place: Place): string {
    return authHref('/login', place)
}

export function signupHref(place: Place): string {
    return authHref('/signup', place)
}

export function authSwitchHref(to: '/login' | '/signup', next: string | null): string {
    return next === null ? to : `${to}?${new URLSearchParams({ next })}`
}

function authHref(to: '/login' | '/signup', { pathname, search, hash }: Place): string {
    if (pathname === '/login' || pathname === '/signup') {
        return authSwitchHref(to, new URLSearchParams(search).get('next'))
    }
    const next = pathname + search + hash
    return authSwitchHref(to, next === '/' ? null : next)
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
