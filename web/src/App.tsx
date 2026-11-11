import { useEffect, useState } from 'react'
import { Navigate, Route, Routes } from 'react-router'
import { type Board, boardKey, latestOnly } from './boards'
import Following from './Following'
import Header from './Header'
import Login from './Login'
import Postings from './Postings'
import RequireLogin from './RequireLogin'
import Signup from './Signup'
import Title from './Title'
import { whilePending } from './pending'
import { trackedRowId, withoutPosting } from './tracked'
import Tracker, { type Tracked } from './Tracker'

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
  const [pendingFollows, setPendingFollows] = useState<Set<string>>(new Set())
  const [pendingTracks, setPendingTracks] = useState<Set<number>>(new Set())

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

  function changeTrack(postingId: number, request: () => Promise<Response>, onDone: (response: Response) => Promise<void>) {
    return whilePending(setPendingTracks, postingId, async () => {
      const response = await request()
      if (!response.ok) {
        setSession(await loadSession())
        return
      }
      await onDone(response)
    })
  }

  function track(postingId: number) {
    return changeTrack(
      postingId,
      () =>
        fetch('/api/me/tracked', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ posting_id: postingId }),
        }),
      async (response) => {
        const tracked: Tracked = await response.json()
        setSession((current) => current && { ...current, tracked: [tracked, ...current.tracked] })
      },
    )
  }

  function untrack(postingId: number) {
    const id = session ? trackedRowId(session.tracked, postingId) : null
    if (id === null) return
    return changeTrack(
      postingId,
      () => fetch(`/api/me/tracked/${id}`, { method: 'DELETE' }),
      async () => setSession((current) => current && { ...current, tracked: withoutPosting(current.tracked, postingId) }),
    )
  }

  async function refreshFollows() {
    const follows = await reloadFollows()
    if (follows) setSession((current) => current && { ...current, follows })
  }

  function changeFollow(source: string, token: string, request: () => Promise<Response>) {
    return whilePending(setPendingFollows, boardKey({ source, token }), async () => {
      await request()
      await refreshFollows()
    })
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

  const tracking = session && {
    ids: new Set(session.tracked.map((row) => row.posting.id)),
    pending: pendingTracks,
    track,
    untrack,
  }
  const following = session && { keys: new Set(session.follows.map(boardKey)), pending: pendingFollows, follow, unfollow }

  const home = (
    <main>
      <Title>kansei · Engineering jobs you can do from Japan</Title>
      {session === null && (
        <div className="pitch">
          <h1>Engineering jobs you can do from Japan.</h1>
          <p>Each posting shows the Japanese level it asks for, so you can filter out the ones that need more than you have.</p>
        </div>
      )}
      <Postings tracking={tracking} following={following} />
    </main>
  )

  return (
    <>
      <Header email={session?.user.email ?? null} onLogOut={logOut} />
      <Routes>
        <Route path="/" element={home} />
        <Route
          path="/tracker"
          element={
            <RequireLogin loggedIn={session !== null}>
              {session && <Tracker tracked={session.tracked} />}
            </RequireLogin>
          }
        />
        <Route path="/tracked" element={<Navigate to="/tracker" replace />} />
        <Route
          path="/following"
          element={
            <RequireLogin loggedIn={session !== null}>
              {session && tracking && following && (
                <Following follows={session.follows} following={following} onFollowsChanged={refreshFollows} tracking={tracking} />
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
