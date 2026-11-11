import { useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import CompanyLogo from './CompanyLogo'
import type { Facts, Posting } from './PostingRow'
import Title from './Title'
import {
    archivedOptionLabel,
    disabledFilters,
    emptyMessage,
    FILTERS,
    filterCounts,
    inOrder,
    LABELS,
    matchesFilter,
    readTrackerView,
    type Stage,
    STAGES,
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
}

function day(iso: string): string {
    return new Date(iso).toLocaleDateString('en-CA')
}

export default function Tracker({ tracked, onMove }: Props) {
    const [searchParams, setSearchParams] = useSearchParams()
    const view = readTrackerView(searchParams)
    const viewKey = trackerViewToSearch(view)
    const [heldOrder, setHeldOrder] = useState(() => ({ viewKey, ids: viewRows(tracked, view).map((row) => row.id) }))

    let ids = heldOrder.ids
    if (heldOrder.viewKey !== viewKey) {
        ids = viewRows(tracked, view).map((row) => row.id)
        setHeldOrder({ viewKey, ids })
    }
    const rows = inOrder(ids, tracked)
    const counts = filterCounts(tracked)
    const disabled = disabledFilters(counts, view.stage)

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
                        onClick={() => setSearchParams(trackerViewToSearch({ ...view, stage: filter }), { replace: true })}
                    >
                        <span className="stage-filter-count">{counts[filter] || '– –'}</span>
                        <span className="stage-filter-label">{LABELS[filter]}</span>
                    </button>
                ))}
            </div>
            <div className="tracker-header">
                <span className="tracker-header-posting">Posting</span>
                <span>Company</span>
                <span>Stage</span>
                <span>Moved</span>
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
                    <li
                        key={row.id}
                        className={row.archived || !matchesFilter(row, view.stage) ? 'tracker-row faded' : 'tracker-row'}
                    >
                        <span className="tracker-chevron" aria-hidden="true">
                            <svg viewBox="0 0 12 12">
                                <path d="M4.5 2.5 8 6l-3.5 3.5" />
                            </svg>
                        </span>
                        <CompanyLogo company={row.posting.company} logoUrl={row.posting.logo_url} />
                        <div className="tracker-title">
                            <a href={row.posting.url} target="_blank" title={row.posting.title}>
                                {row.posting.title}
                            </a>
                            {!row.posting.listed && <span className="unlisted">No longer listed</span>}
                        </div>
                        <span className="tracker-company">{row.posting.company}</span>
                        <select
                            className={`stage-pill stage-${row.archived ? 'archived' : row.stage}`}
                            aria-label={`Stage of ${row.posting.title}`}
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
                    </li>
                ))}
            </ul>
        </main>
    )
}
