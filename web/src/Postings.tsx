import { useEffect, useState } from "react";
import { useSearchParams } from "react-router";
import { boardKey, followsKey } from "./boards";
import { type Filters, filtersToSearch, readFilters } from "./filters";
import { capitalize, JAPANESE_CHOICES, japaneseRequirement, passesJapanese, readJapaneseChoice } from "./japanese";
import PostingRow, { type Facts, type Posting } from "./PostingRow";
import { checkedAgo, lastChecked } from "./checked";

type Row = {
    posting: Posting
    facts: Facts
    sales_or_support: boolean
}

type Props = {
    followingOnly?: boolean
    trackedIds: Set<number> | null
    pendingTracks: Set<number>
    onTrack: (postingId: number) => void
    onUntrack: (postingId: number) => void
    followed: Set<string> | null
    pendingFollows: Set<string>
    onFollow: (source: string, token: string) => void
    onUnfollow: (source: string, token: string) => void
}

export default function Postings({ followingOnly = false, trackedIds, pendingTracks, onTrack, onUntrack, followed, pendingFollows, onFollow, onUnfollow }: Props) {
    const [rows, setRows] = useState<Row[] | undefined>(undefined)
    const [searchParams, setSearchParams] = useSearchParams()
    const filters = readFilters(searchParams)
    const [failed, setFailed] = useState(false)
    const [now] = useState(Date.now)

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
    const checkedAt = followingOnly ? null : lastChecked(rows)

    function postingAction(posting: Posting) {
        if (!trackedIds) return null
        const isTracked = trackedIds.has(posting.id)
        return (
            <button
                className={isTracked ? 'track tracked' : 'track'}
                aria-pressed={isTracked}
                aria-label={isTracked ? `Untrack ${posting.title}` : `Track ${posting.title}`}
                disabled={pendingTracks.has(posting.id)}
                onClick={() => isTracked ? onUntrack(posting.id) : onTrack(posting.id)}
            >
                {isTracked ? '✓ Tracked' : 'Track'}
            </button>
        )
    }

    function companyAction(posting: Posting) {
        if (!followed || !posting.has_board) return null
        const key = boardKey(posting)
        const isFollowed = followed.has(key)
        return (
            <button
                className={isFollowed ? 'follow followed' : 'follow'}
                aria-pressed={isFollowed}
                aria-label={isFollowed ? `Unfollow ${posting.company}` : `Follow ${posting.company}`}
                disabled={pendingFollows.has(key)}
                onClick={() => isFollowed ? onUnfollow(posting.source, posting.token) : onFollow(posting.source, posting.token)}
            >
                {isFollowed ? 'Following ✓' : '+ Follow'}
            </button>
        )
    }

    function setFilters(change: Partial<Filters>) {
        setSearchParams(filtersToSearch({ ...filters, ...change }), { replace: true })
    }

    return (
        <section>
            <div className="postings-heading">
                <h2>Postings ({visible.length})</h2>
                {checkedAt && <span className="muted">checked {checkedAgo(checkedAt, now)}</span>}
            </div>
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
                    <PostingRow key={posting.id} posting={posting} facts={facts} actions={postingAction(posting)} companyAction={companyAction(posting)} />
                ))}
            </ul>
        </section>
    )
}
