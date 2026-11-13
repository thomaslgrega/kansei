import { expect, test } from 'vitest'
import { AUTH_COPY, logOut, submitAuth } from './auth'

type Sent = { url: string; method?: string; headers?: HeadersInit; body?: BodyInit | null }

function fakeFetch(response: Response) {
    const sent: Sent[] = []
    const fetchFn = async (url: RequestInfo | URL, init?: RequestInit) => {
        sent.push({ url: String(url), method: init?.method, headers: init?.headers, body: init?.body })
        return response
    }
    return { sent, fetchFn }
}

const credentials = { email: 'a@example.com', password: 'correct horse battery staple' }

test('logging in posts the credentials to the login endpoint', async () => {
    const { sent, fetchFn } = fakeFetch(new Response(null, { status: 204 }))

    expect(await submitAuth('login', credentials, fetchFn)).toBe(null)
    expect(sent).toEqual([
        {
            url: '/api/login',
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: '{"email":"a@example.com","password":"correct horse battery staple"}',
        },
    ])
})

test('signing up posts the credentials to the signup endpoint', async () => {
    const { sent, fetchFn } = fakeFetch(new Response('{}', { status: 201 }))

    expect(await submitAuth('signup', credentials, fetchFn)).toBe(null)
    expect(sent).toEqual([
        {
            url: '/api/signup',
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: '{"email":"a@example.com","password":"correct horse battery staple"}',
        },
    ])
})

test('a rejected login reads as a wrong email or password', async () => {
    const { fetchFn } = fakeFetch(new Response(null, { status: 401 }))

    expect(await submitAuth('login', credentials, fetchFn)).toBe('Wrong email or password')
})

test('a rejected signup reads its reason from the response body', async () => {
    const body = JSON.stringify({ detail: [{ type: 'string_too_short', loc: ['body', 'password'] }] })
    const { fetchFn } = fakeFetch(new Response(body, { status: 422 }))

    expect(await submitAuth('signup', credentials, fetchFn)).toBe('The password needs at least 15 characters.')
})

test('a signup error without a JSON body still has a message', async () => {
    const { fetchFn } = fakeFetch(new Response('Bad Gateway', { status: 502 }))

    expect(await submitAuth('signup', credentials, fetchFn)).toBe('Something went wrong. Try again.')
})

test('logging out posts to the logout endpoint and lands on the home page, from any page', async () => {
    const { sent, fetchFn } = fakeFetch(new Response(null, { status: 204 }))

    expect(await logOut(fetchFn)).toBe('/')
    expect(sent).toEqual([{ url: '/api/logout', method: 'POST', headers: undefined, body: undefined }])
})

test('each form carries the copy from the design', () => {
    expect(AUTH_COPY).toEqual({
        login: {
            title: 'Log in · kansei',
            heading: 'Welcome back',
            subtitle: 'Log in to see your tracker and the companies you follow.',
            button: 'Log in',
            pending: 'Logging in…',
            switchPrompt: 'New here?',
            switchLink: 'Create an account',
        },
        signup: {
            title: 'Sign up · kansei',
            heading: 'Create an account',
            subtitle: 'Track postings and follow the companies you want to work for.',
            button: 'Create account',
            pending: 'Creating account…',
            switchPrompt: 'Have an account?',
            switchLink: 'Log in',
        },
    })
})
