import { type SubmitEvent, useState } from 'react'
import { boardKey } from './boards'

type Hit = {
    source: string
    token: string
    company: string | null
    titles: string[]
    candidates: number
    state: 'not_on_kansei' | 'on_kansei' | 'removed'
    following: boolean
}

type Probe = { hits: Hit[]; message: string | null }

const REMOVED = "This company was removed from kansei and can't be added."
const FAILED: Probe = { hits: [], message: "Couldn't search. Try again." }

type Props = {
    followed: Set<string>
    onFollowsChanged: () => Promise<void>
}

export default function AddCompany({ followed, onFollowsChanged }: Props) {
    const [probe, setProbe] = useState<Probe | null>(null)
    const [searching, setSearching] = useState(false)
    const [adding, setAdding] = useState<string | null>(null)
    const [notice, setNotice] = useState('')

    async function find(event: SubmitEvent<HTMLFormElement>) {
        event.preventDefault()
        const q = String(new FormData(event.currentTarget).get('q') ?? '')
        setSearching(true)
        setNotice('')
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
        const key = boardKey(hit)
        const name = hit.company ?? hit.token
        setAdding(key)
        setNotice('')
        try {
            const response = await fetch('/api/me/follows', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ source: hit.source, token: hit.token }),
            })
            if (!response.ok) {
                const body = await response.json().catch(() => null)
                setNotice(typeof body?.detail === 'string' ? body.detail : `Couldn't add ${name}. Try again.`)
                return
            }
            setNotice(
                hit.state === 'not_on_kansei'
                    ? `Added ${name}. Its jobs will appear after the next update.`
                    : `Following ${name}.`,
            )
            setProbe((current) => current && {
                ...current,
                hits: current.hits.map((other) => (boardKey(other) === key ? { ...other, state: 'on_kansei' } : other)),
            })
            await onFollowsChanged()
        } finally {
            setAdding(null)
        }
    }

    function action(hit: Hit) {
        if (hit.state === 'removed') return <p className="status">{REMOVED}</p>
        if (followed.has(boardKey(hit))) return <span className="status">Following</span>
        return (
            <button disabled={adding === boardKey(hit)} onClick={() => add(hit)}>
                {hit.state === 'not_on_kansei' ? 'Add' : 'Follow'}
            </button>
        )
    }

    return (
        <>
            <form onSubmit={find}>
                <input name="q" type="text" placeholder="Company name, or a Greenhouse, Lever or Ashby board or job URL" required />
                <button disabled={searching}>Find company</button>
            </form>
            {probe?.message && <p role="status">{probe.message}</p>}
            <ul>
                {probe?.hits.map((hit) => (
                    <li key={boardKey(hit)}>
                        <strong>{hit.company ?? hit.token}</strong>{' '}
                        <span className="status">
                            {hit.source} · {hit.candidates} Japan engineering {hit.candidates === 1 ? 'job' : 'jobs'} open now
                        </span>
                        <p className="status">{hit.titles.length > 0 ? hit.titles.join(' · ') : 'No open jobs'}</p>
                        {action(hit)}
                    </li>
                ))}
            </ul>
            {notice && <p role="status">{notice}</p>}
        </>
    )
}
