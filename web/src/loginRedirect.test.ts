import { expect, test } from 'vitest'
import { loginHref, returnTo } from './loginRedirect'

test('the login link remembers the page it was followed from', () => {
    const pages = [
        { pathname: '/', search: '', hash: '' },
        { pathname: '/tracked', search: '', hash: '' },
        { pathname: '/tracked', search: '?status=applied', hash: '#12' },
        { pathname: '/login', search: '?next=%2Ftracked', hash: '' },
        { pathname: '/login', search: '', hash: '' },
    ]

    expect(pages.map(loginHref)).toEqual([
        '/login',
        '/login?next=%2Ftracked',
        '/login?next=%2Ftracked%3Fstatus%3Dapplied%2312',
        '/login?next=%2Ftracked',
        '/login',
    ])
})

test('after login, returns only to a page on this site, and never to login itself', () => {
    const next = [
        null,
        '',
        '/',
        '/tracked?status=applied#12',
        '//evil.example',
        '/\\evil.example',
        'https://evil.example/',
        'tracked',
        '/login',
        '/login?next=%2Ftracked',
    ]

    expect(next.map(returnTo)).toEqual([
        '/',
        '/',
        '/',
        '/tracked?status=applied#12',
        '/',
        '/',
        '/',
        '/',
        '/',
        '/',
    ])
})
