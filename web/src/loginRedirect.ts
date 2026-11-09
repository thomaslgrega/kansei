type Place = { pathname: string; search: string; hash: string }

const HERE = 'https://kansei.invalid'

export function loginHref({ pathname, search, hash }: Place): string {
    if (pathname === '/login') return `/login${search}`
    const next = pathname + search + hash
    return next === '/' ? '/login' : `/login?${new URLSearchParams({ next })}`
}

export function returnTo(next: string | null): string {
    if (!next?.startsWith('/')) return '/'
    const url = new URL(next, HERE)
    return url.origin !== HERE || url.pathname === '/login' ? '/' : next
}
