export type Stage = 'saved' | 'applied' | 'interviewing' | 'offer'
export type Filter = Stage | 'all' | 'archived'
export type TrackerView = { stage: Filter }
export type Counts = Record<Filter, number>

type Staged = { stage: Stage; archived: boolean }
type Movable = Staged & { id: number; moved_at: string }

export const STAGES: Stage[] = ['saved', 'applied', 'interviewing', 'offer']
export const FILTERS: Filter[] = ['all', ...STAGES, 'archived']

export const LABELS: Record<Filter, string> = {
    all: 'All',
    saved: 'Saved',
    applied: 'Applied',
    interviewing: 'Interviewing',
    offer: 'Offer',
    archived: 'Archived',
}

function isFilter(value: string | null): value is Filter {
    return (FILTERS as (string | null)[]).includes(value)
}

export function readTrackerView(params: URLSearchParams): TrackerView {
    const stage = params.get('stage')
    return { stage: isFilter(stage) ? stage : 'all' }
}

export function trackerViewToSearch(view: TrackerView): string {
    const params = new URLSearchParams()
    if (view.stage !== 'all') params.set('stage', view.stage)
    return params.toString()
}

export function matchesFilter(row: Staged, filter: Filter): boolean {
    if (filter === 'archived') return row.archived
    return !row.archived && (filter === 'all' || row.stage === filter)
}

export function viewRows<T extends Movable>(rows: T[], view: TrackerView): T[] {
    return rows
        .filter((row) => matchesFilter(row, view.stage))
        .sort((a, b) => Date.parse(b.moved_at) - Date.parse(a.moved_at) || b.id - a.id)
}

export function filterCounts(rows: Staged[]): Counts {
    return Object.fromEntries(FILTERS.map((filter) => [filter, rows.filter((row) => matchesFilter(row, filter)).length])) as Counts
}

export function disabledFilters(counts: Counts, selected: Filter): Filter[] {
    return FILTERS.filter((filter) => counts[filter] === 0 && filter !== selected)
}

export function inOrder<T extends { id: number }>(ids: number[], rows: T[]): T[] {
    const byId = new Map(rows.map((row) => [row.id, row]))
    return ids.flatMap((id) => byId.get(id) ?? [])
}

export function archivedOptionLabel(row: Staged): string {
    return row.archived ? `Archived · ${LABELS[row.stage]}` : 'Archived'
}

export function emptyMessage(filter: Filter): string {
    if (filter === 'all') return 'Nothing in progress.'
    if (filter === 'archived') return 'Nothing archived.'
    return `Nothing in ${LABELS[filter]}.`
}
