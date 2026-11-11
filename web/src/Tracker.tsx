import { useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import CompanyLogo from './CompanyLogo'
import Dropdown from './Dropdown'
import type { Facts, Posting } from './PostingRow'
import { allPostingChips } from './chips'
import PostingChips from './PostingChips'
import Title from './Title'
import UntrackConfirm from './UntrackConfirm'
import {
    archivedOptionLabel,
    asksBeforeUntrack,
    clickSort,
    disabledFilters,
    emptyMessage,
    FILTERS,
    filterCounts,
    flipOrder,
    inOrder,
    LABELS,
    matchesFilter,
    type Order,
    orderLabel,
    pickSort,
    readTrackerView,
    type Sort,
    SORT_COLUMNS,
    SORT_OPTIONS,
    type Stage,
    STAGES,
    type TrackerView,
    trackerViewToSearch,
    viewRows,
} from './trackerView'

export type Tracked = {
    id: number
    stage: Stage
    archived: boolean
    note: string
    tracked_at: string
    moved_at: string
    posting: Posting & { listed: boolean }
    facts: Facts | null
}

export type Move = { stage: Stage } | { archived: true }

type Props = {
    tracked: Tracked[]
    onMove: (id: number, move: Move) => void
    onNote: (id: number, note: string) => void
    onUntrack: (postingId: number) => void
}

const HEADER_SORTS: Sort[] = ['company', 'stage', 'moved']
const ARROWS: Record<Order, string> = { asc: '▲', desc: '▼' }

function day(iso: string): string {
    return new Date(iso).toLocaleDateString('en-CA')
}

export default function Tracker({ tracked, onMove, onNote, onUntrack }: Props) {
    const [searchParams, setSearchParams] = useSearchParams()
    const view = readTrackerView(searchParams)
    const viewKey = trackerViewToSearch(view)
    const [expanded, setExpanded] = useState<Set<number>>(new Set())
    const [heldOrder, setHeldOrder] = useState(() => ({ viewKey, ids: viewRows(tracked, view).map((row) => row.id) }))

    let ids = heldOrder.ids
    if (heldOrder.viewKey !== viewKey) {
        ids = viewRows(tracked, view).map((row) => row.id)
        setHeldOrder({ viewKey, ids })
    }
    const setView = (next: TrackerView) => setSearchParams(trackerViewToSearch(next), { replace: true })
    const direction = orderLabel(view.sort, view.order)
    const rows = inOrder(ids, tracked)
    const counts = filterCounts(tracked)
    const disabled = disabledFilters(counts, view.stage)

    function toggle(id: number) {
        setExpanded((current) => {
            const next = new Set(current)
            if (!next.delete(id)) next.add(id)
            return next
        })
    }

    return (
        <main>
            <Title>Tracker · kansei</Title>
            <h1>Tracker</h1>
            <div className="stage-filters" role="group" aria-label="Filter by stage">
                {FILTERS.map((filter) => (
                    <button
                        key={filter}
                        type="button"
                        className={`stage-filter stage-${filter}`}
                        aria-pressed={filter === view.stage}
                        disabled={disabled.includes(filter)}
                        onClick={() => setView({ ...view, stage: filter })}
                    >
                        <span className="stage-filter-count">{counts[filter] || '– –'}</span>
                        <span className="stage-filter-label">{LABELS[filter]}</span>
                    </button>
                ))}
            </div>
            <div className="tracker-sortbar">
                <Dropdown label="Sort by" options={SORT_OPTIONS} value={view.sort} onChange={(sort) => setView(pickSort(view, sort))} />
                <button
                    type="button"
                    className="tracker-sort-flip"
                    aria-label={direction}
                    title={direction}
                    onClick={() => setView(flipOrder(view))}
                >
                    {ARROWS[view.order]}
                </button>
            </div>
            <div className="tracker-header">
                <span className="tracker-header-posting">Posting</span>
                {HEADER_SORTS.map((sort) => {
                    const { label } = SORT_COLUMNS[sort]
                    const active = sort === view.sort
                    return (
                        <button
                            key={sort}
                            type="button"
                            className="tracker-sort"
                            aria-pressed={active}
                            aria-label={active ? `${label}, ${direction}` : label}
                            onClick={() => setView(clickSort(view, sort))}
                        >
                            {label}
                            <span className="tracker-sort-arrow" aria-hidden="true">
                                {active && ARROWS[view.order]}
                            </span>
                        </button>
                    )
                })}
            </div>
            {tracked.length === 0 ? (
                <p className="tracker-empty">
                    <Link to="/">Track postings</Link> from the postings page to follow them here.
                </p>
            ) : (
                rows.length === 0 && <p className="tracker-empty">{emptyMessage(view.stage)}</p>
            )}
            <ul className="tracker">
                {rows.map((row) => (
                    <TrackerRow
                        key={row.id}
                        row={row}
                        faded={row.archived || !matchesFilter(row, view.stage)}
                        expanded={expanded.has(row.id)}
                        onToggle={() => toggle(row.id)}
                        onExpand={() => setExpanded((current) => new Set(current).add(row.id))}
                        onMove={onMove}
                        onNote={onNote}
                        onUntrack={onUntrack}
                    />
                ))}
            </ul>
        </main>
    )
}

type RowProps = Pick<Props, 'onMove' | 'onNote' | 'onUntrack'> & {
    row: Tracked
    faded: boolean
    expanded: boolean
    onToggle: () => void
    onExpand: () => void
}

function TrackerRow({ row, faded, expanded, onToggle, onExpand, onMove, onNote, onUntrack }: RowProps) {
    const [confirming, setConfirming] = useState(false)
    const title = row.posting.title
    const preview = row.note.trim().split('\n')[0]
    const detailsId = `tracker-details-${row.id}`

    return (
        <li
            className={`tracker-row${faded ? ' faded' : ''}${expanded ? ' expanded' : ''}`}
            onClick={(event) => {
                // Controls, the company name and the open details keep their clicks; the chevron is the keyboard path.
                if ((event.target as Element).closest('a, button, select, textarea, .tracker-company, .tracker-details')) return
                if (window.getSelection()?.toString()) return
                onToggle()
            }}
        >
            <button
                type="button"
                className="tracker-chevron"
                aria-expanded={expanded}
                aria-controls={detailsId}
                aria-label={`Details of ${title}`}
                onClick={onToggle}
            >
                <svg viewBox="0 0 12 12" aria-hidden="true">
                    <path d="M4.5 2.5 8 6l-3.5 3.5" />
                </svg>
            </button>
            <CompanyLogo company={row.posting.company} logoUrl={row.posting.logo_url} />
            <div className="tracker-title">
                <div className="tracker-title-line">
                    <a href={row.posting.url} target="_blank" title={title}>
                        {title}
                    </a>
                    {!row.posting.listed && <span className="unlisted">No longer listed</span>}
                </div>
                {!expanded && preview && (
                    <button type="button" className="tracker-note-preview" onClick={onExpand}>
                        {preview}
                    </button>
                )}
            </div>
            <span className="tracker-company">{row.posting.company}</span>
            <select
                className={`stage-pill stage-${row.archived ? 'archived' : row.stage}`}
                aria-label={`Stage of ${title}`}
                value={row.archived ? 'archived' : row.stage}
                onChange={(event) => {
                    const value = event.target.value
                    onMove(row.id, value === 'archived' ? { archived: true } : { stage: value as Stage })
                }}
            >
                {STAGES.map((stage) => (
                    <option key={stage} value={stage}>
                        {LABELS[stage]}
                    </option>
                ))}
                <option disabled value="">
                    ──────
                </option>
                <option value="archived">{archivedOptionLabel(row)}</option>
            </select>
            <time className="tracker-moved" dateTime={row.moved_at} title={`Tracked ${day(row.tracked_at)}`}>
                {day(row.moved_at)}
            </time>
            {expanded && (
                <div className="tracker-details" id={detailsId}>
                    <textarea
                        key={row.note}
                        className="tracker-note"
                        aria-label={`Note on ${title}`}
                        placeholder="Add a note"
                        maxLength={2000}
                        rows={3}
                        defaultValue={row.note}
                        onBlur={(event) => {
                            if (event.target.value !== row.note) onNote(row.id, event.target.value)
                        }}
                    />
                    {row.facts && <p className="tracker-summary">{row.facts.role_summary}</p>}
                    <p className="muted">{row.posting.location}</p>
                    <p className="muted">
                        Tracked <time dateTime={row.tracked_at}>{day(row.tracked_at)}</time> · Moved{' '}
                        <time dateTime={row.moved_at}>{day(row.moved_at)}</time>
                    </p>
                    {row.facts && <PostingChips chips={allPostingChips(row.facts)} />}
                    <div className="tracker-actions">
                        <a href={row.posting.url} target="_blank">
                            Open posting
                        </a>
                        {confirming ? (
                            <UntrackConfirm onUntrack={() => onUntrack(row.posting.id)} onKeep={() => setConfirming(false)} />
                        ) : (
                            <button
                                type="button"
                                className="untrack"
                                onClick={() => (asksBeforeUntrack(row) ? setConfirming(true) : onUntrack(row.posting.id))}
                            >
                                Untrack
                            </button>
                        )}
                    </div>
                </div>
            )}
        </li>
    )
}
