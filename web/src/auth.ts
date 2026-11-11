import { loginError } from './loginError'
import { signupError } from './signupError'

export type AuthMode = 'login' | 'signup'

type Credentials = { email: string; password: string }

type Copy = {
    title: string
    heading: string
    subtitle: string
    button: string
    pending: string
    switchPrompt: string
    switchLink: string
}

export const AUTH_COPY = {
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
} satisfies Record<AuthMode, Copy>

async function errorFor(mode: AuthMode, response: Response): Promise<string> {
    if (mode === 'login') return loginError(response.status)
    return signupError(response.status, await response.json().catch(() => null))
}

// Returns the message to show, or null when the server accepted the credentials.
export async function submitAuth(mode: AuthMode, credentials: Credentials, fetchFn = fetch): Promise<string | null> {
    const response = await fetchFn(`/api/${mode}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(credentials),
    })
    return response.ok ? null : errorFor(mode, response)
}
