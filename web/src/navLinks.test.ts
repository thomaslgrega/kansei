import { expect, test } from 'vitest'
import { navLinks } from './navLinks'

function at(pathname: string, search = '') {
    return { pathname, search, hash: '' }
}

test('logged out, shows Log in and Sign up, marking the one whose page is open', () => {
    expect(navLinks(false, at('/'))).toEqual([
        { label: 'Log in', to: '/login', look: 'link', current: false },
        { label: 'Sign up', to: '/signup', look: 'button', current: false },
    ])
    expect(navLinks(false, at('/login', '?next=%2Ftracker'))).toEqual([
        { label: 'Log in', to: '/login?next=%2Ftracker', look: 'link', current: true },
        { label: 'Sign up', to: '/signup', look: 'button', current: false },
    ])
    expect(navLinks(false, at('/signup'))).toEqual([
        { label: 'Log in', to: '/login?next=%2Fsignup', look: 'link', current: false },
        { label: 'Sign up', to: '/signup', look: 'button', current: true },
    ])
})

test('logged in, shows Postings, Following and Tracker, with Postings current only on the home page', () => {
    expect(navLinks(true, at('/'))).toEqual([
        { label: 'Postings', to: '/', look: 'link', current: true },
        { label: 'Following', to: '/following', look: 'link', current: false },
        { label: 'Tracker', to: '/tracker', look: 'link', current: false },
    ])
    expect(navLinks(true, at('/following'))).toEqual([
        { label: 'Postings', to: '/', look: 'link', current: false },
        { label: 'Following', to: '/following', look: 'link', current: true },
        { label: 'Tracker', to: '/tracker', look: 'link', current: false },
    ])
    expect(navLinks(true, at('/tracker', '?stage=applied'))).toEqual([
        { label: 'Postings', to: '/', look: 'link', current: false },
        { label: 'Following', to: '/following', look: 'link', current: false },
        { label: 'Tracker', to: '/tracker', look: 'link', current: true },
    ])
})
