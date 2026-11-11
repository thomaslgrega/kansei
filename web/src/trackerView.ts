export type Stage = 'saved' | 'applied' | 'interviewing' | 'offer'
export type Filter = Stage | 'all' | 'archived'
export type Sort = 'moved' | 'company' | 'stage'
export type Order = 'asc' | 'desc'
export type TrackerView = { stage: Filter; sort: Sort; order: Order }
export type Counts = Record<Filter, number>

type Staged = { stage: Stage; archived: boolean }
type Movable = Staged & { id: number; moved_at: string; posting: { company: string } }

export const STAGES: Stage[] = ['saved', 'applied', 'interviewing', 'offer']
export const FILTERS: Filter[] = ['all', ...STAGES, 'archived']
export const SORTS: Sort[] = ['moved', 'company', 'stage']
const FIRST_ORDER: Record<Sort, Order> = { moved: 'desc', company: 'asc', stage: 'asc' }

const ORDER_LABELS: Record<Sort, Record<Order, string>> = {
    moved: { asc: 'Oldest first', desc: 'Newest first' },
    company: { asc: 'A to Z', desc: 'Z to A' },
    stage: { asc: 'Saved first', desc: 'Offer first' },
}

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

function isSort(value: string | null): value is Sort {
    return (SORTS as (string | null)[]).includes(value)
}

export function readTrackerView(params: URLSearchParams): TrackerView {
    const stage = params.get('stage')
    const sort = params.get('sort')
    const order = params.get('order')
    const view = { stage: isFilter(stage) ? stage : 'all', sort: isSort(sort) ? sort : 'moved' } as const
    return { ...view, order: order === 'asc' || order === 'desc' ? order : FIRST_ORDER[view.sort] }
}

export function trackerViewToSearch(view: TrackerView): string {
    const params = new URLSearchParams()
    if (view.stage !== 'all') params.set('stage', view.stage)
    if (view.sort !== 'moved') params.set('sort', view.sort)
    if (view.order !== FIRST_ORDER[view.sort]) params.set('order', view.order)
    return params.toString()
}

export function clickSort(view: TrackerView, sort: Sort): TrackerView {
    return sort === view.sort ? flipOrder(view) : { ...view, sort, order: FIRST_ORDER[sort] }
}

export function pickSort(view: TrackerView, sort: Sort): TrackerView {
    return sort === view.sort ? view : { ...view, sort, order: FIRST_ORDER[sort] }
}

export function flipOrder(view: TrackerView): TrackerView {
    return { ...view, order: view.order === 'asc' ? 'desc' : 'asc' }
}

export function orderLabel(sort: Sort, order: Order): string {
    return ORDER_LABELS[sort][order]
}

export function matchesFilter(row: Staged, filter: Filter): boolean {
    if (filter === 'archived') return row.archived
    return !row.archived && (filter === 'all' || row.stage === filter)
}

function newestFirst(a: Movable, b: Movable): number {
    return Date.parse(b.moved_at) - Date.parse(a.moved_at) || b.id - a.id
}

function ascending(sort: Sort, a: Movable, b: Movable): number {
    if (sort === 'company') return a.posting.company.localeCompare(b.posting.company, 'ja')
    if (sort === 'stage') return STAGES.indexOf(a.stage) - STAGES.indexOf(b.stage)
    return -newestFirst(a, b)
}

export function viewRows<T extends Movable>(rows: T[], view: TrackerView): T[] {
    const sign = view.order === 'asc' ? 1 : -1
    return rows
        .filter((row) => matchesFilter(row, view.stage))
        .sort((a, b) => sign * ascending(view.sort, a, b) || newestFirst(a, b))
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

export function asksBeforeUntrack(row: Staged & { note: string }): boolean {
    return row.note.trim() !== '' || row.stage !== 'saved' || row.archived
}

export function emptyMessage(filter: Filter): string {
    if (filter === 'all') return 'Nothing in progress.'
    if (filter === 'archived') return 'Nothing archived.'
    return `Nothing in ${LABELS[filter]}.`
}
