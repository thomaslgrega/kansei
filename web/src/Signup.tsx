import { type SubmitEvent, useState } from 'react'
import { Navigate } from 'react-router'
import { signupError } from './signupError'
import Title from './Title'

type Props = {
    loggedIn: boolean
    onSignedUp: () => Promise<void>
}

export default function Signup({ loggedIn, onSignedUp }: Props) {
    const [error, setError] = useState('')

    if (loggedIn) return <Navigate to="/following" replace />

    async function signUp(event: SubmitEvent<HTMLFormElement>) {
        event.preventDefault()
        const form = new FormData(event.currentTarget)
        const response = await fetch('/api/signup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: form.get('email'), password: form.get('password') }),
        })
        if (!response.ok) {
            setError(signupError(response.status, await response.json().catch(() => null)))
            return
        }
        await onSignedUp()
    }

    return (
        <main>
            <Title>Sign up · kansei</Title>
            <h1>Sign up</h1>
            <form onSubmit={signUp}>
                <input name="email" type="email" placeholder="Email" autoComplete="email" required />
                <input
                    name="password"
                    type="password"
                    placeholder="Password"
                    autoComplete="new-password"
                    aria-describedby="password-hint"
                    required
                />
                <small id="password-hint" className="muted">At least 15 characters. A few words work.</small>
                <button>Sign up</button>
                {error && <p role="alert">{error}</p>}
            </form>
        </main>
    )
}
