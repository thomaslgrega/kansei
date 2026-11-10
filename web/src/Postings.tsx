import { useEffect, useState } from "react";
import { useSearchParams } from "react-router";
import { boardKey, followsKey } from "./boards";
import { type Filters, filtersToSearch, readFilters } from "./filters";
import {
    capitalize,
    JAPANESE_CHOICES,
    type JapaneseFacts,
    japaneseBadge,
    japaneseRequirement,
    passesJapanese,
    readJapaneseChoice,
} from "./japanese";
import NewBadge from "./NewBadge";

type Facts = JapaneseFacts & {
    role_summary: string
    seniority: string
    must_have_skills: string[]
    remote_policy: string
}

type Row = {
    posting: {
        id: number
        url: string
        source: string
        token: string
        company: string
        has_board: boolean
        title: string
        location: string
        first_seen_at: string
    }
    facts: Facts
    sales_or_support: boolean
}

function factLine(facts: Facts): string {
    return [facts.remote_policy, facts.seniority, facts.jlpt]
        .filter((value) => value !== 'not_stated')
        .join(' · ')
}

type Props = {
    followingOnly?: boolean
    trackedIds: Set<number> | null
    onTrack: (postingId: number) => void
    followed: Set<string> | null
    pendingFollows: Set<string>
    onFollow: (source: string, token: string) => void
    onUnfollow: (source: string, token: string) => void
}

export default function Postings({ followingOnly = false, trackedIds, onTrack, followed, pendingFollows, onFollow, onUnfollow }: Props) {
    const [rows, setRows] = useState<Row[] | undefined>(undefined)
    const [searchParams, setSearchParams] = useSearchParams()
    const filters = readFilters(searchParams)
    const [failed, setFailed] = useState(false)

    // Refetch when follows change, so a newly followed board's postings join the list.
    const followsSignature = followingOnly && followed ? followsKey(followed) : ''

    useEffect(() => {
        let current = true
        const url = followingOnly ? '/api/postings?following=true' : '/api/postings'
        fetch(url)
            .then((response) => {
                if (!response.ok) throw new Error(`GET ${url}: ${response.status}`)
                return response.json()
            })
            .then((rows) => {
                if (!current) return
                setRows(rows)
                setFailed(false)
            })
            .catch(() => current && setFailed(true))
        return () => {
            current = false
        }
    }, [followingOnly, followsSignature])

    if (failed) return <p>Couldn't load postings. Try reloading the page.</p>
    if (rows === undefined) return <p>Loading postings...</p>

    // An unfollowed board's postings leave at once, without waiting for the refetch.
    const shown = followingOnly && followed ? rows.filter(({ posting }) => followed.has(boardKey(posting))) : rows
    const passing = shown.filter(({ facts }) => passesJapanese(japaneseRequirement(facts), filters.japanese))
    const hidden = passing.filter((row) => row.sales_or_support).length
    const visible = filters.showSales ? passing : passing.filter((row) => !row.sales_or_support)

    function setFilters(change: Partial<Filters>) {
        setSearchParams(filtersToSearch({ ...filters, ...change }), { replace: true })
    }

    return (
        <section>
            <h2>Postings ({visible.length})</h2>
            <div className="filters">
                <label>
                    My Japanese{' '}
                    <select
                        value={filters.japanese}
                        onChange={(event) => setFilters({ japanese: readJapaneseChoice(event.target.value) })}
                    >
                        {JAPANESE_CHOICES.map((choice) => (
                            <option key={choice} value={choice}>{capitalize(choice)}</option>
                        ))}
                    </select>
                </label>
                <label>
                    <input type="checkbox" checked={filters.showSales} onChange={(event) => setFilters({ showSales: event.target.checked })} />
                    Show sales and support roles ({hidden})
                </label>
            </div>
            <ul className="postings">
                {visible.map(({ posting, facts }) => (
                    <li key={posting.id}>
                        <NewBadge firstSeenAt={posting.first_seen_at} />
                        <a href={posting.url} target="_blank">
                            {posting.title}
                        </a>
                        {' '}<span className="japanese">{japaneseBadge(facts)}</span>
                        <p className="status">
                            {posting.company}
                            {followed && posting.has_board && (followed.has(boardKey(posting)) ? (
                                <> <button disabled={pendingFollows.has(boardKey(posting))} onClick={() => onUnfollow(posting.source, posting.token)}>Unfollow</button></>
                            ) : (
                                <> <button disabled={pendingFollows.has(boardKey(posting))} onClick={() => onFollow(posting.source, posting.token)}>Follow</button></>
                            ))}
                            {' '}· {posting.location} · first seen {new Date(posting.first_seen_at).toLocaleDateString('en-CA')}
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
