import { type SubmitEvent, useState } from 'react'
import { Link, Navigate, useSearchParams } from 'react-router'
import { AUTH_COPY, type AuthMode, submitAuth } from './auth'
import { afterSignup, authSwitchHref, returnTo } from './loginRedirect'
import Title from './Title'

type Props = {
    mode: AuthMode
    loggedIn: boolean
    onAuthenticated: () => Promise<void>
}

function EyeIcon({ crossed }: { crossed: boolean }) {
    return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z" />
            <circle cx="12" cy="12" r="3" />
            {crossed && <path d="M4 4l16 16" />}
        </svg>
    )
}

export default function AuthForm({ mode, loggedIn, onAuthenticated }: Props) {
    const [error, setError] = useState('')
    const [pending, setPending] = useState(false)
    const [passwordShown, setPasswordShown] = useState(false)
    const [params] = useSearchParams()
    const next = params.get('next')
    const copy = AUTH_COPY[mode]
    const signup = mode === 'signup'

    if (loggedIn) return <Navigate to={signup ? afterSignup(next) : returnTo(next)} replace />

    async function submit(event: SubmitEvent<HTMLFormElement>) {
        event.preventDefault()
        const form = new FormData(event.currentTarget)
        const credentials = { email: String(form.get('email')), password: String(form.get('password')) }
        setPending(true)
        try {
            const message = await submitAuth(mode, credentials)
            if (message === null) await onAuthenticated()
            else setError(message)
        } finally {
            setPending(false)
        }
    }

    return (
        <main className="auth">
            <Title>{copy.title}</Title>
            <h1>{copy.heading}</h1>
            <p className="auth-subtitle muted">{copy.subtitle}</p>
            <form onSubmit={submit}>
                <label className="auth-field">
                    Email
                    <input name="email" type="email" placeholder="you@example.com" autoComplete="email" required />
                </label>
                <div className="auth-field">
                    <label htmlFor="password">Password</label>
                    <span className="auth-password">
                        <input
                            id="password"
                            name="password"
                            type={passwordShown ? 'text' : 'password'}
                            autoComplete={signup ? 'new-password' : 'current-password'}
                            aria-describedby={signup ? 'password-hint' : undefined}
                            required
                        />
                        <button
                            type="button"
                            className="auth-eye"
                            aria-label="Show password"
                            aria-pressed={passwordShown}
                            onClick={() => setPasswordShown(!passwordShown)}
                        >
                            <EyeIcon crossed={passwordShown} />
                        </button>
                    </span>
                </div>
                {signup && (
                    <small id="password-hint" className="muted">
                        At least 15 characters. A few words work.
                    </small>
                )}
                {error && (
                    <p className="auth-error" role="alert">
                        {error}
                    </p>
                )}
                <button className="auth-submit" disabled={pending}>
                    {pending ? (
                        copy.pending
                    ) : (
                        <>
                            {copy.button} <span aria-hidden="true">→</span>
                        </>
                    )}
                </button>
            </form>
            <p className="auth-switch">
                <span className="muted">{copy.switchPrompt}</span>{' '}
                <Link to={authSwitchHref(signup ? '/login' : '/signup', next)}>{copy.switchLink}</Link>
            </p>
        </main>
    )
}
