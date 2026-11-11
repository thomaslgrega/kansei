import { useEffect, useState } from "react";
import { useSearchParams } from "react-router";
import { boardKey, type FollowControls, followsKey } from "./boards";
import { type Filters, filtersToSearch, readFilters } from "./filters";
import { capitalize, JAPANESE_CHOICES, japaneseRequirement, passesJapanese, readJapaneseChoice } from "./japanese";
import PostingRow, { type Facts, type Posting } from "./PostingRow";
import { checkedAgo, lastChecked } from "./checked";
import type { TrackControls } from "./tracked";
import UntrackConfirm from "./UntrackConfirm";

type Row = {
    posting: Posting
    facts: Facts
    sales_or_support: boolean
}

type Props = {
    followingOnly?: boolean
    tracking: TrackControls | null
    following: FollowControls | null
}

export default function Postings({ followingOnly = false, tracking, following }: Props) {
    const [rows, setRows] = useState<Row[] | undefined>(undefined)
    const [searchParams, setSearchParams] = useSearchParams()
    const filters = readFilters(searchParams)
    const [failed, setFailed] = useState(false)
    const [now] = useState(Date.now)

    // Refetch when follows change, so a newly followed board's postings join the list.
    const followsSignature = followingOnly && following ? followsKey(following.keys) : ''

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
    const shown = followingOnly && following ? rows.filter(({ posting }) => following.keys.has(boardKey(posting))) : rows
    const passing = shown.filter(({ facts }) => passesJapanese(japaneseRequirement(facts), filters.japanese))
    const hidden = passing.filter((row) => row.sales_or_support).length
    const visible = filters.showSales ? passing : passing.filter((row) => !row.sales_or_support)
    const checkedAt = followingOnly ? null : lastChecked(rows)

    function companyAction(posting: Posting) {
        if (!following || !posting.has_board) return null
        const key = boardKey(posting)
        const isFollowed = following.keys.has(key)
        return (
            <button
                className={isFollowed ? 'follow followed' : 'follow'}
                aria-pressed={isFollowed}
                aria-label={isFollowed ? `Unfollow ${posting.company}` : `Follow ${posting.company}`}
                disabled={following.pending.has(key)}
                onClick={() => isFollowed ? following.unfollow(posting.source, posting.token) : following.follow(posting.source, posting.token)}
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
                    <PostingRow
                        key={posting.id}
                        posting={posting}
                        facts={facts}
                        actions={tracking && <TrackToggle posting={posting} tracking={tracking} />}
                        companyAction={companyAction(posting)}
                    />
                ))}
            </ul>
        </section>
    )
}

function TrackToggle({ posting, tracking }: { posting: Posting; tracking: TrackControls }) {
    const [confirming, setConfirming] = useState(false)
    const isTracked = tracking.ids.has(posting.id)

    if (confirming && isTracked) {
        return (
            <UntrackConfirm
                onUntrack={() => {
                    setConfirming(false)
                    tracking.untrack(posting.id)
                }}
                onKeep={() => setConfirming(false)}
            />
        )
    }

    function toggle() {
        if (!isTracked) {
            setConfirming(false)
            tracking.track(posting.id)
        } else if (tracking.asksBeforeUntrackingPosting(posting.id)) setConfirming(true)
        else tracking.untrack(posting.id)
    }

    return (
        <button
            className={isTracked ? 'track tracked' : 'track'}
            aria-pressed={isTracked}
            aria-label={isTracked ? `Untrack ${posting.title}` : `Track ${posting.title}`}
            disabled={tracking.pending.has(posting.id)}
            onClick={toggle}
        >
            {isTracked ? '✓ Tracked' : 'Track'}
        </button>
    )
}
