import { type SubmitEvent, useEffect, useState } from 'react'

type User = { id: number; email: string }

type Tracked = {
  id: number
  status: string
  note: string
  posting: { id: number; title: string; url: string; location: string }
}

type Session = { user: User; tracked: Tracked[] }

async function loadSession(): Promise<Session | null> {
  const me = await fetch('/api/me')
  if (me.status === 401) return null
  const tracked = await fetch('/api/me/tracked')
  return { user: await me.json(), tracked: await tracked.json() }
}

export default function App() {
  const [session, setSession] = useState<Session | null | undefined>(undefined)
  const [error, setError] = useState('')

  useEffect(() => {
    loadSession().then(setSession)
  }, [])

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
    setError('')
    setSession(await loadSession())
  }

  async function logOut() {
    await fetch('/api/logout', { method: 'POST' })
    setSession(null)
  }

  if (session === undefined) return null

  if (session === null) {
    return (
      <main>
        <h1>kansei</h1>
        <form onSubmit={logIn}>
          <input name="email" type="email" placeholder="Email" required />
          <input name="password" type="password" placeholder="Password" required />
          <button>Log in</button>
          {error && <p role="alert">{error}</p>}
        </form>
      </main>
    )
  }

  return (
    <main>
      <h1>kansei</h1>
      <p>
        {session.user.email} · <button onClick={logOut}>Log out</button>
      </p>
      <h2>Tracked postings</h2>
      <ul>
        {session.tracked.map((row) => (
          <li key={row.id}>
            <a href={row.posting.url}>{row.posting.title}</a>
            <br />
            <span className="status">
              {row.status} · {row.posting.location}
            </span>
          </li>
        ))}
      </ul>
    </main>
  )
}
