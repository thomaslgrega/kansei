import { expect, test } from 'vitest'
import { loginHref, returnTo } from './loginRedirect'

test('the login link remembers the page it was followed from', () => {
    const pages = [
        { pathname: '/', search: '', hash: '' },
        { pathname: '/tracker', search: '', hash: '' },
        { pathname: '/tracker', search: '?status=applied', hash: '#12' },
        { pathname: '/login', search: '?next=%2Ftracker', hash: '' },
        { pathname: '/login', search: '', hash: '' },
    ]

    expect(pages.map(loginHref)).toEqual([
        '/login',
        '/login?next=%2Ftracker',
        '/login?next=%2Ftracker%3Fstatus%3Dapplied%2312',
        '/login?next=%2Ftracker',
        '/login',
    ])
})

test('after login, returns only to a page on this site, and never to login itself', () => {
    const next = [
        null,
        '',
        '/',
        '/tracker?status=applied#12',
        '/tracked',
        '//evil.example',
        '/\\evil.example',
        'https://evil.example/',
        'tracker',
        '/login',
        '/login?next=%2Ftracker',
    ]

    expect(next.map(returnTo)).toEqual([
        '/',
        '/',
        '/',
        '/tracker?status=applied#12',
        '/tracked',
        '/',
        '/',
        '/',
        '/',
        '/',
        '/',
    ])
})
