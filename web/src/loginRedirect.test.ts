import { expect, test } from 'vitest'
import { afterSignup, authSwitchHref, loginHref, returnTo, signupHref } from './loginRedirect'

test('the login and signup links remember the page they were followed from', () => {
    const pages = [
        { pathname: '/', search: '', hash: '' },
        { pathname: '/tracker', search: '', hash: '' },
        { pathname: '/tracker', search: '?status=applied', hash: '#12' },
        { pathname: '/login', search: '?next=%2Ftracker', hash: '' },
        { pathname: '/login', search: '', hash: '' },
        { pathname: '/signup', search: '?next=%2Ffollowing%3Fadd%3DStripe', hash: '' },
        { pathname: '/signup', search: '', hash: '' },
    ]

    expect(pages.map(loginHref)).toEqual([
        '/login',
        '/login?next=%2Ftracker',
        '/login?next=%2Ftracker%3Fstatus%3Dapplied%2312',
        '/login?next=%2Ftracker',
        '/login',
        '/login?next=%2Ffollowing%3Fadd%3DStripe',
        '/login',
    ])
    expect(pages.map(signupHref)).toEqual([
        '/signup',
        '/signup?next=%2Ftracker',
        '/signup?next=%2Ftracker%3Fstatus%3Dapplied%2312',
        '/signup?next=%2Ftracker',
        '/signup',
        '/signup?next=%2Ffollowing%3Fadd%3DStripe',
        '/signup',
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

test('the link between login and signup carries next over unchanged', () => {
    const links = [
        authSwitchHref('/signup', null),
        authSwitchHref('/signup', '/tracker?status=applied#12'),
        authSwitchHref('/login', null),
        authSwitchHref('/login', '/tracker'),
        authSwitchHref('/login', '//evil.example'),
    ]

    expect(links).toEqual([
        '/signup',
        '/signup?next=%2Ftracker%3Fstatus%3Dapplied%2312',
        '/login',
        '/login?next=%2Ftracker',
        '/login?next=%2F%2Fevil.example',
    ])
})

test('after signup, goes to a safe next, or else to Following', () => {
    const next = [
        null,
        '',
        '/',
        '/tracker?status=applied#12',
        '//evil.example',
        '/\\evil.example',
        'https://evil.example/',
        '/login',
    ]

    expect(next.map(afterSignup)).toEqual([
        '/following',
        '/following',
        '/',
        '/tracker?status=applied#12',
        '/following',
        '/following',
        '/following',
        '/following',
    ])
})
