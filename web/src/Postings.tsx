import { useEffect, useState } from "react";
import { useSearchParams } from "react-router";
import { boardKey, followsKey } from "./boards";
import { type Filters, filtersToSearch, readFilters } from "./filters";
import { capitalize, JAPANESE_CHOICES, japaneseRequirement, passesJapanese, readJapaneseChoice } from "./japanese";
import PostingRow, { type Facts, type Posting } from "./PostingRow";

type Row = {
    posting: Posting
    facts: Facts
    sales_or_support: boolean
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

    function actions(posting: Posting) {
        if (!trackedIds && !followed) return null
        const key = boardKey(posting)
        return (
            <>
                {trackedIds && (trackedIds.has(posting.id) ? (
                    <span className="muted">Tracked</span>
                ) : (
                    <button onClick={() => onTrack(posting.id)}>Track</button>
                ))}
                {followed && posting.has_board && (followed.has(key) ? (
                    <button disabled={pendingFollows.has(key)} onClick={() => onUnfollow(posting.source, posting.token)} aria-label={`Unfollow ${posting.company}`}>
                        Unfollow
                    </button>
                ) : (
                    <button disabled={pendingFollows.has(key)} onClick={() => onFollow(posting.source, posting.token)} aria-label={`Follow ${posting.company}`}>
                        Follow
                    </button>
                ))}
            </>
        )
    }

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
                    <PostingRow key={posting.id} posting={posting} facts={facts} actions={actions(posting)} />
                ))}
            </ul>
        </section>
    )
}
