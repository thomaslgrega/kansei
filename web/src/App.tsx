import { useEffect, useState } from 'react'
import { Route, Routes } from 'react-router'
import { type Board, boardKey, latestOnly } from './boards'
import Following from './Following'
import Header from './Header'
import Login from './Login'
import Postings from './Postings'
import RequireLogin from './RequireLogin'
import Signup from './Signup'
import Title from './Title'
import TrackedPostings, { type Tracked } from './TrackedPostings'

type User = { id: number; email: string }

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

  const trackedIds = session && new Set(session.tracked.map((row) => row.posting.id))

  const home = (
    <main>
      <Title>kansei · Engineering jobs you can do from Japan</Title>
      {session === null && (
        <div className="pitch">
          <h1>Engineering jobs you can do from Japan.</h1>
          <p>Each posting shows the Japanese level it asks for, so you can filter out the ones that need more than you have.</p>
        </div>
      )}
      <Postings
        trackedIds={trackedIds}
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
        <Route
          path="/tracked"
          element={
            <RequireLogin loggedIn={session !== null}>
              {session && <TrackedPostings tracked={session.tracked} />}
            </RequireLogin>
          }
        />
        <Route
          path="/following"
          element={
            <RequireLogin loggedIn={session !== null}>
              {session && trackedIds && (
                <Following
                  follows={session.follows}
                  pendingFollows={pending}
                  onFollow={follow}
                  onUnfollow={unfollow}
                  onFollowsChanged={refreshFollows}
                  trackedIds={trackedIds}
                  onTrack={track}
                />
              )}
            </RequireLogin>
          }
        />
        <Route path="/login" element={<Login loggedIn={session !== null} onLoggedIn={reloadSession} />} />
        <Route path="/signup" element={<Signup loggedIn={session !== null} onSignedUp={reloadSession} />} />
        <Route path="*" element={<main><Title>Not found · kansei</Title><p>Page not found.</p></main>} />
      </Routes>
    </>
  )
}
