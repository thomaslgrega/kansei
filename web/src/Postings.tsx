import { useEffect, useState } from "react";

type Facts = {
    role_summary: string
    seniority: string
    must_have_skills: string[]
    japanese_required: string
    japanese_level: string
    jlpt: string
    remote_policy: string
}

type Row = {
    posting: { id: number; url: string; token: string; title: string; location: string; first_seen_at: string }
    facts: Facts
    sales_or_support: boolean
}

function factLine(facts: Facts): string {
    const japanese = facts.japanese_required === 'not_stated' ? 'Japanese not stated' : `Japanese ${facts.japanese_required}`
    return [japanese, facts.japanese_level, facts.jlpt, facts.remote_policy, facts.seniority]
        .filter((value) => value !== 'not_stated')
        .join(' · ')
}

type Props = { trackedIds: Set<number> | null; onTrack: (postingId: number) => void }

export default function Postings({ trackedIds, onTrack }: Props) {
    const [rows, setRows] = useState<Row[] | undefined>(undefined)
    const [showSales, setShowSales] = useState(false)
    const [failed, setFailed] = useState(false)

    useEffect(() => {
        fetch('/api/postings')
            .then((response) => {
                if (!response.ok) throw new Error(`GET /api/postings: ${response.status}`)
                return response.json()
            })
            .then(setRows)
            .catch(() => setFailed(true))
    }, [])

    if (failed) return <p>Couldn't load postings. Try reloading the page.</p>
    if (rows === undefined) return <p>Loading postings...</p>

    const hidden = rows.filter((row) => row.sales_or_support).length
    const visible = showSales ? rows : rows.filter((row) => !row.sales_or_support)

    return (
        <section>
            <h2>Postings ({visible.length})</h2>
            <label>
                <input type="checkbox" checked={showSales} onChange={(event) => setShowSales(event.target.checked)} />
                Show sales and support roles ({hidden})
            </label>
            <ul className="postings">
                {visible.map(({ posting, facts }) => (
                    <li key={posting.id}>
                        <a href={posting.url} target="_blank">
                            {posting.title}
                        </a>
                        <p className="status">
                            {posting.token} · {posting.location} · first seen {new Date(posting.first_seen_at).toLocaleDateString('en-CA')}
                        </p>
                        <p className="facts">{factLine(facts)}</p>
                        {facts.must_have_skills.length > 0 && <p className="status">{facts.must_have_skills.join(', ')}</p>}
                        <p>{facts.role_summary}</p>
                        {trackedIds && (trackedIds.has(posting.id) ?
                            (
                                <span className="status">Tracked</span>
                            ) : (
                                <button onClick={() => onTrack(posting.id)}>Track</button>
                            ))}
                    </li>
                ))}
            </ul>
        </section>
    )
}
