import { type SubmitEvent, useState } from 'react'
import { Navigate, useSearchParams } from 'react-router'
import { returnTo } from './loginRedirect'
import Title from './Title'

type Props = {
    loggedIn: boolean
    onLoggedIn: () => Promise<void>
}

export default function Login({ loggedIn, onLoggedIn }: Props) {
    const [error, setError] = useState('')
    const [params] = useSearchParams()

    if (loggedIn) return <Navigate to={returnTo(params.get('next'))} replace />

    async function logIn(event: SubmitEvent<HTMLFormElement>) {
        event.preventDefault()
        const form = new FormData(event.currentTarget)
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: form.get('email'), password: form.get('password') }),
        })
        if (!response.ok) {
            setError('Wrong email or password')
            return
        }
        await onLoggedIn()
    }

    return (
        <main>
            <Title>Log in · kansei</Title>
            <h1>Log in</h1>
            <form onSubmit={logIn}>
                <input name="email" type="email" placeholder="Email" required />
                <input name="password" type="password" placeholder="Password" required />
                <button>Log in</button>
                {error && <p role="alert">{error}</p>}
            </form>
        </main>
    )
}
