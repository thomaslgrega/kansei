import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { boardKey, type FollowControls, followsKey } from "./boards";
import { type Filters, filtersToSearch, postingsUrl, readFilters } from "./filters";
import Dropdown from "./Dropdown";
import { JAPANESE_OPTIONS, type JapaneseRequirement } from "./japanese";
import PostingRow, { type Facts, type Posting } from "./PostingRow";
import { checkedAgo, lastChecked } from "./checked";
import type { TrackControls } from "./tracked";
import SpecialtyFilter from "./SpecialtyFilter";
import UntrackConfirm from "./UntrackConfirm";

type Row = {
    posting: Posting
    facts: Facts
    japanese_requirement: JapaneseRequirement
}

type Props = {
    followingOnly?: boolean
    tracking: TrackControls | null
    following: FollowControls | null
}

export default function Postings({ followingOnly = false, tracking, following }: Props) {
    const [rows, setRows] = useState<Row[] | undefined>(undefined)
    const [searchParams] = useSearchParams()
    const navigate = useNavigate()
    const filters = readFilters(searchParams)
    const url = postingsUrl(followingOnly, filters)
    const [failed, setFailed] = useState(false)
    const [now] = useState(Date.now)

    // Refetch when follows change, so a newly followed board's postings join the list.
    const followsSignature = followingOnly && following ? followsKey(following.keys) : ''

    useEffect(() => {
        let current = true
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
    }, [url, followsSignature])

    if (failed) return <p>Couldn't load postings. Try reloading the page.</p>
    if (rows === undefined) return <p>Loading postings...</p>

    // An unfollowed board's postings leave at once, without waiting for the refetch.
    const shown = followingOnly && following ? rows.filter(({ posting }) => following.keys.has(boardKey(posting))) : rows
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
        // Not setSearchParams, which would write the commas in `specialty` as %2C.
        navigate(`?${filtersToSearch({ ...filters, ...change })}`, { replace: true })
    }

    return (
        <section>
            <div className="postings-heading">
                <h2>Postings ({shown.length})</h2>
                {checkedAt && <span className="muted">checked {checkedAgo(checkedAt, now)}</span>}
            </div>
            <div className="filters">
                <Dropdown label="My Japanese" options={JAPANESE_OPTIONS} value={filters.japanese} onChange={(japanese) => setFilters({ japanese })} />
                <SpecialtyFilter selected={filters.specialties} onChange={(specialties) => setFilters({ specialties })} />
            </div>
            {filters.specialties?.length === 0 && <p className="muted">No specialties selected.</p>}
            <ul className="postings">
                {shown.map(({ posting, facts, japanese_requirement }) => (
                    <PostingRow
                        key={posting.id}
                        posting={posting}
                        facts={facts}
                        japaneseRequirement={japanese_requirement}
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
