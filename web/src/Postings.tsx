import { Fragment, type SubmitEvent, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { boardKey, type FollowControls, followsKey } from "./boards";
import { correctedSearch, emptyMessage, type Filters, filtersToSearch, postingsUrl, querySearch, readFilters, servedQuery, showAllSearch, type WhyEmpty } from "./filters";
import Dropdown from "./Dropdown";
import { JAPANESE_OPTIONS, type JapaneseRequirement } from "./japanese";
import { lastPage, pageNumbers, pageRange, readPage } from "./pages";
import PostingRow, { type Facts, type Posting } from "./PostingRow";
import { checkedAgo } from "./checked";
import { addCompanyHref, boardHref, companiesLine, type MatchedBoard } from "./companies";
import type { TrackControls } from "./tracked";
import ShowingOnly from "./ShowingOnly";
import SpecialtyFilter from "./SpecialtyFilter";
import UntrackConfirm from "./UntrackConfirm";

type Row = {
    posting: Posting
    facts: Facts
    japanese_requirement: JapaneseRequirement
}

type AskedBoard = { source: string; token: string; company: string; removed: boolean; why_empty: WhyEmpty | null }

type PostingsPage = {
    postings: Row[]
    total: number
    page: number
    checked_at: string | null
    board: AskedBoard | null
    matched_boards: MatchedBoard[]
    filtered_out: boolean
}

type Props = {
    followingOnly?: boolean
    tracking: TrackControls | null
    following: FollowControls | null
}

export default function Postings({ followingOnly = false, tracking, following }: Props) {
    const [loaded, setLoaded] = useState<{ url: string; body: PostingsPage } | undefined>(undefined)
    const [searchParams] = useSearchParams()
    const navigate = useNavigate()
    const read = readFilters(searchParams, followingOnly && following ? following.keys : undefined)
    // The Following page has no search box, so a stray `q` mustn't narrow it unseen.
    const filters = followingOnly ? { ...read, query: '' } : read
    const url = postingsUrl(followingOnly, filters, readPage(searchParams))
    const [failed, setFailed] = useState(false)
    const [now] = useState(Date.now)
    const top = useRef<HTMLElement>(null)

    // Refetch when follows change, so a newly followed board's postings join the list and later pages move up.
    const followsSignature = followingOnly && following ? followsKey(following.keys) : ''

    useEffect(() => {
        let current = true
        fetch(url)
            .then((response) => {
                if (!response.ok) throw new Error(`GET ${url}: ${response.status}`)
                return response.json()
            })
            .then((body: PostingsPage) => {
                if (!current) return
                setLoaded({ url, body })
                setFailed(false)
            })
            .catch(() => current && setFailed(true))
        return () => {
            current = false
        }
    }, [url, followsSignature])

    // Only an answer to the URL now shown may correct it, not one for the page just left.
    const served = loaded?.url === url ? loaded.body : null
    const corrected = served !== null ? correctedSearch(searchParams, filters, served) : null
    useEffect(() => {
        if (corrected !== null) navigate(`?${corrected}`, { replace: true })
    }, [corrected, navigate])

    if (failed) return <p>Couldn't load postings. Try reloading the page.</p>
    if (loaded === undefined) return <p>Loading postings...</p>

    const { postings: rows, page, checked_at: checkedAt } = loaded.body
    // An unfollowed board's postings leave at once, without waiting for the refetch.
    const shown = followingOnly && following ? rows.filter(({ posting }) => following.keys.has(boardKey(posting))) : rows
    const total = loaded.body.total - (rows.length - shown.length)
    const last = lastPage(total)
    // The last answer's board, kept while the next page of it loads.
    const narrowed = !followingOnly && loaded.body.board !== null && boardKey(loaded.body.board) === filters.board
        ? loaded.body.board
        : null
    // Rows still shown from the previous search are marked by the query they were found with.
    const loadedQuery = servedQuery(loaded.url)
    // The last answer's companies, kept while the next page of the same search loads.
    const matched = !followingOnly && filters.query !== '' && loadedQuery === filters.query ? loaded.body.matched_boards : null
    const empty = !followingOnly && served !== null ? emptyMessage(filters, served, narrowed) : null

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

    function pageLink(to: number, label: string, current = false) {
        return (
            <Link
                key={label}
                to={`?${filtersToSearch(filters, to)}`}
                aria-current={current ? 'page' : undefined}
                onClick={() => top.current?.scrollIntoView()}
            >
                {label}
            </Link>
        )
    }

    return (
        <section ref={top}>
            <div className="postings-heading">
                <h2>Postings ({total})</h2>
                {checkedAt && !followingOnly && <span className="muted">checked {checkedAgo(checkedAt, now)}</span>}
            </div>
            {!followingOnly && (
                <SearchBox query={filters.query} onSearch={(typed) => navigate(`?${querySearch(filters, typed)}`, { replace: true })} />
            )}
            <div className="filters">
                <Dropdown label="My Japanese" options={JAPANESE_OPTIONS} value={filters.japanese} onChange={(japanese) => setFilters({ japanese })} />
                <SpecialtyFilter selected={filters.specialties} onChange={(specialties) => setFilters({ specialties })} />
            </div>
            {narrowed && (
                <ShowingOnly company={narrowed.company} onShowAll={() => navigate(`?${showAllSearch(filters)}`, { replace: true })} />
            )}
            {matched !== null && <CompaniesLine matched={matched} filters={filters} />}
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
                        query={loadedQuery}
                    />
                ))}
            </ul>
            {empty?.kind === 'just_added' && (
                <p className="muted">{empty.company} was added after the last update. Its jobs will appear after the next one.</p>
            )}
            {empty?.kind === 'nothing_to_show' && (
                <p className="muted">kansei reads {empty.company}'s board, but has no Japan engineering jobs to show from it right now.</p>
            )}
            {empty?.kind === 'removed' && <p className="muted">{empty.company} was removed from kansei.</p>}
            {empty?.kind === 'filtered' && (
                <p className="muted">
                    {empty.company === null ? 'No jobs' : `No ${empty.company} jobs`} match your filters ·{' '}
                    <Link to={empty.clear} replace>Clear filters</Link>
                </p>
            )}
            {empty?.kind === 'query' && <p className="muted">No jobs match "{empty.query}".</p>}
            {empty?.kind === 'plain' && <p className="muted">No postings match.</p>}
            {last > 1 && (
                <nav className="pager" aria-label="Pages">
                    {page > 1 ? pageLink(page - 1, 'Prev') : <span className="muted">Prev</span>}
                    {pageNumbers(page, last).map((number, index) =>
                        number === '…' ? <span key={`gap-${index}`} className="muted">…</span> : pageLink(number, String(number), number === page)
                    )}
                    {page < last ? pageLink(page + 1, 'Next') : <span className="muted">Next</span>}
                    <span className="muted pager-range">{pageRange(page, total)}</span>
                </nav>
            )}
        </section>
    )
}

function CompaniesLine({ matched, filters }: { matched: MatchedBoard[]; filters: Filters }) {
    const line = companiesLine(matched)
    const query = filters.query
    if (line.kind === 'one') {
        const { company } = line.board
        return (
            <p className="companies-line">
                {company} is on kansei · <Link to={boardHref(filters, line.board)}>Only {company}'s jobs →</Link>
            </p>
        )
    }
    if (line.kind === 'none') {
        return (
            <p className="companies-line">
                {line.ending.kind === 'add' ? (
                    <>
                        No company called "{query}" on kansei.{' '}
                        <Link to={addCompanyHref(query)}>Add it, and its jobs show up here for everyone →</Link>
                    </>
                ) : (
                    `${line.ending.company} was removed from kansei.`
                )}
            </p>
        )
    }
    return (
        <p className="companies-line">
            Companies matching "{query}":{' '}
            {line.boards.map((board, index) => (
                <Fragment key={boardKey(board)}>
                    {index > 0 && ', '}
                    <Link to={boardHref(filters, board)}>{board.company} →</Link>
                </Fragment>
            ))}
            {line.ending?.kind === 'add' && (
                <>
                    {' '}Not the {query} you meant? <Link to={addCompanyHref(query)}>Add it to kansei →</Link>
                </>
            )}
            {line.ending?.kind === 'removed' && ` ${line.ending.company} was removed from kansei.`}
        </p>
    )
}

function SearchBox({ query, onSearch }: { query: string; onSearch: (typed: string) => void }) {
    const [typed, setTyped] = useState(query)
    const [applied, setApplied] = useState(query)
    const input = useRef<HTMLInputElement>(null)
    // A link can change the query too, as the Postings link clears it.
    if (query !== applied) {
        setApplied(query)
        setTyped(query)
    }

    function submit(event: SubmitEvent<HTMLFormElement>) {
        event.preventDefault()
        onSearch(typed)
    }

    function clear() {
        setTyped('')
        if (query !== '') onSearch('')
        input.current?.focus()
    }

    return (
        <form className="company-search postings-search" role="search" onSubmit={submit}>
            <label className="company-search-field">
                <svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true">
                    <circle cx="8.5" cy="8.5" r="5.5" fill="none" stroke="currentColor" strokeWidth="2" />
                    <path d="M13 13l4.5 4.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
                <input
                    ref={input}
                    type="search"
                    aria-label="Search postings"
                    placeholder="Company, title or skill"
                    value={typed}
                    onChange={(event) => setTyped(event.target.value)}
                />
                {(typed !== '' || query !== '') && (
                    <button type="button" className="search-clear" aria-label="Clear search" onClick={clear}>✕</button>
                )}
            </label>
            <button className="company-search-go">Search</button>
        </form>
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
