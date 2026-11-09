import { useEffect, useState } from 'react'
import { Route, Routes } from 'react-router'
import AddCompany from './AddCompany'
import { type Board, boardKey, latestOnly } from './boards'
import Header from './Header'
import Login from './Login'
import NewBadge from './NewBadge'
import Postings from './Postings'
import Title from './Title'

type User = { id: number; email: string }

type Tracked = {
  id: number
  status: string
  note: string
  posting: { id: number; title: string; url: string; location: string; first_seen_at: string; listed: boolean }
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
  const [pending, setPending] = useState<Set<string>>(new Set())

  useEffect(() => {
    loadSession().then(setSession)
  }, [])

  async function reloadSession() {
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

  const home = (
    <main>
      <Title>kansei</Title>
      {session !== null && (
        <>
          <h2>Tracked postings</h2>
          <ul>
            {session.tracked.map((row) => (
              <li key={row.id}>
                <NewBadge firstSeenAt={row.posting.first_seen_at} />
                <a href={row.posting.url}>{row.posting.title}</a>
                <br />
                <span className="status">
                  {row.status} · {row.posting.location}
                  {!row.posting.listed && ' · No longer listed'}
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

  return (
    <>
      <Header email={session?.user.email ?? null} onLogOut={logOut} />
      <Routes>
        <Route path="/" element={home} />
        <Route path="/login" element={<Login loggedIn={session !== null} onLoggedIn={reloadSession} />} />
        <Route path="*" element={<main><Title>Not found · kansei</Title><p>Page not found.</p></main>} />
      </Routes>
    </>
  )
}
