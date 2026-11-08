import { type SubmitEvent, useEffect, useState } from 'react'
import AddCompany from './AddCompany'
import { type Board, boardKey, latestOnly } from './boards'
import NewBadge from './NewBadge'
import Postings from './Postings'

type User = { id: number; email: string }

type Tracked = {
  id: number
  status: string
  note: string
  posting: { id: number; title: string; url: string; location: string; first_seen_at: string }
}

type Session = { user: User; tracked: Tracked[]; follows: Board[] }

async function loadFollows(): Promise<Board[]> {
  return (await fetch('/api/me/follows')).json()
}

const reloadFollows = latestOnly(loadFollows)

async function loadSession(): Promise<Session | null> {
  const me = await fetch('/api/me')
  if (me.status === 401) return null
  const [tracked, follows] = await Promise.all([fetch('/api/me/tracked'), loadFollows()])
  return { user: await me.json(), tracked: await tracked.json(), follows }
}

export default function App() {
  const [session, setSession] = useState<Session | null | undefined>(undefined)
  const [error, setError] = useState('')
  const [pending, setPending] = useState<Set<string>>(new Set())

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

  async function track(postingId: number) {
    const response = await fetch('/api/me/tracked', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ posting_id: postingId }),
    })
    if (!response.ok) {
      setSession(await loadSession())
      return
    }
    const tracked: Tracked = await response.json()
    setSession((current) => current && { ...current, tracked: [tracked, ...current.tracked] })
  }

  async function refreshFollows() {
    const follows = await reloadFollows()
    if (follows) setSession((current) => current && { ...current, follows })
  }

  async function changeFollow(source: string, token: string, request: () => Promise<Response>) {
    const key = boardKey({ source, token })
    setPending((current) => new Set(current).add(key))
    try {
      await request()
      await refreshFollows()
    } finally {
      setPending((current) => {
        const next = new Set(current)
        next.delete(key)
        return next
      })
    }
  }

  function follow(source: string, token: string) {
    return changeFollow(source, token, () =>
      fetch('/api/me/follows', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source, token }),
      }),
    )
  }

  function unfollow(source: string, token: string) {
    return changeFollow(source, token, () =>
      fetch(`/api/me/follows/${encodeURIComponent(source)}/${encodeURIComponent(token)}`, { method: 'DELETE' }),
    )
  }

  if (session === undefined) return null

  return (
    <main>
      <h1>kansei</h1>
      {session === null ? (
        <form onSubmit={logIn}>
          <input name="email" type="email" placeholder="Email" required />
          <input name="password" type="password" placeholder="Password" required />
          <button>Log in</button>
          {error && <p role="alert">{error}</p>}
        </form>
      ) : (
        <>
          <p>
            {session.user.email} · <button onClick={logOut}>Log out</button>
          </p>
          <h2>Tracked postings</h2>
          <ul>
            {session.tracked.map((row) => (
              <li key={row.id}>
                <NewBadge firstSeenAt={row.posting.first_seen_at} />
                <a href={row.posting.url}>{row.posting.title}</a>
                <br />
                <span className="status">
                  {row.status} · {row.posting.location}
                </span>
              </li>
            ))}
          </ul>
          <h2>Following</h2>
          <ul>
            {session.follows.map((board) => (
              <li key={boardKey(board)}>
                {board.company}{' '}
                <button disabled={pending.has(boardKey(board))} onClick={() => unfollow(board.source, board.token)}>
                  Unfollow
                </button>
              </li>
            ))}
          </ul>
          <AddCompany followed={new Set(session.follows.map(boardKey))} onFollowsChanged={refreshFollows} />
        </>
      )}
      <Postings
        trackedIds={session && new Set(session.tracked.map((row) => row.posting.id))}
        onTrack={track}
        followed={session && new Set(session.follows.map(boardKey))}
        pendingFollows={pending}
        onFollow={follow}
        onUnfollow={unfollow}
      />
    </main>
  )
}
