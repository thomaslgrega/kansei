import { type SubmitEvent, useState } from 'react'
import { boardKey } from './boards'
import CompanyLogo from './CompanyLogo'
import { candidateCountLabel, followedNotice, type Hit, hitAction, hitName } from './probeHits'

type Probe = { hits: Hit[]; message: string | null }

const REMOVED = "This company was removed from kansei and can't be added."
const FAILED: Probe = { hits: [], message: "Couldn't search. Try again." }

type Props = {
    followed: Set<string>
    onFollowsChanged: () => Promise<void>
    onFollowed: (notice: string) => void
    autoFocus?: boolean
}

export default function AddCompany({ followed, onFollowsChanged, onFollowed, autoFocus }: Props) {
    const [probe, setProbe] = useState<Probe | null>(null)
    const [searching, setSearching] = useState(false)
    const [adding, setAdding] = useState<string | null>(null)
    const [error, setError] = useState('')

    async function find(event: SubmitEvent<HTMLFormElement>) {
        event.preventDefault()
        const q = String(new FormData(event.currentTarget).get('q') ?? '')
        setSearching(true)
        setError('')
        try {
            const response = await fetch(`/api/probe?q=${encodeURIComponent(q)}`)
            setProbe(response.ok ? await response.json() : FAILED)
        } catch {
            setProbe(FAILED)
        } finally {
            setSearching(false)
        }
    }

    async function add(hit: Hit) {
        setAdding(boardKey(hit))
        setError('')
        try {
            const response = await fetch('/api/me/follows', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ source: hit.source, token: hit.token }),
            })
            if (!response.ok) {
                const body = await response.json().catch(() => null)
                setError(typeof body?.detail === 'string' ? body.detail : `Couldn't add ${hitName(hit)}. Try again.`)
                return
            }
            await onFollowsChanged()
            onFollowed(followedNotice(hit))
        } finally {
            setAdding(null)
        }
    }

    function action(hit: Hit) {
        const shown = hitAction(hit, followed)
        if (shown === 'removed') return null
        if (shown === 'following') return <span className="hit-following">Following ✓</span>
        return (
            <button className="hit-follow" disabled={adding === boardKey(hit)} onClick={() => add(hit)}>
                {shown === 'add' ? '+ Add' : '+ Follow'}
            </button>
        )
    }

    return (
        <div className="add-company">
            <form className="company-search" onSubmit={find}>
                <label className="company-search-field">
                    <svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true">
                        <circle cx="8.5" cy="8.5" r="5.5" fill="none" stroke="currentColor" strokeWidth="2" />
                        <path d="M13 13l4.5 4.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                    </svg>
                    <input
                        name="q"
                        type="search"
                        aria-label="Company name or board URL"
                        placeholder="Company name, or a Greenhouse, Lever, Ashby or HRMOS URL"
                        autoFocus={autoFocus}
                        required
                    />
                </label>
                <button className="company-search-go" disabled={searching}>{searching ? 'Searching…' : 'Search'}</button>
            </form>
            {probe?.message && <p className="muted" role="status">{probe.message}</p>}
            {error && <p role="status">{error}</p>}
            {probe && probe.hits.length > 0 && (
                <ul className="hits">
                    {probe.hits.map((hit) => (
                        <li key={boardKey(hit)} className={hit.state === 'removed' ? 'hit removed' : 'hit'}>
                            <CompanyLogo company={hitName(hit)} logoUrl={hit.logo_url} />
                            <div className="hit-body">
                                <div className="hit-name">
                                    <strong>{hitName(hit)}</strong>
                                    <span className="hit-source">{hit.source}</span>
                                </div>
                                {hit.state === 'removed' ? (
                                    <p className="muted">{REMOVED}</p>
                                ) : (
                                    <>
                                        <p className="hit-count">{candidateCountLabel(hit.candidates)}</p>
                                        {hit.titles.length > 0 ? (
                                            <ul className="hit-titles">
                                                {hit.titles.map((title, index) => <li key={index}>{title}</li>)}
                                            </ul>
                                        ) : (
                                            <p className="muted">No open jobs</p>
                                        )}
                                    </>
                                )}
                            </div>
                            <div className="hit-action">{action(hit)}</div>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    )
}
