export type Stage = 'saved' | 'applied' | 'interviewing' | 'offer'
export type Filter = Stage | 'all' | 'archived'
export type Sort = 'moved' | 'company' | 'stage'
export type Order = 'asc' | 'desc'
export type TrackerView = { stage: Filter; sort: Sort; order: Order }
export type Counts = Record<Filter, number>

type Staged = { stage: Stage; archived: boolean }
type TrackerRow = Staged & { id: number; moved_at: string; posting: { company: string } }

type SortColumn = {
    label: string
    hint: string
    firstOrder: Order
    orderLabels: Record<Order, string>
    compare: (a: TrackerRow, b: TrackerRow) => number
}

export const STAGES: Stage[] = ['saved', 'applied', 'interviewing', 'offer']
export const FILTERS: Filter[] = ['all', ...STAGES, 'archived']
export const SORTS: Sort[] = ['moved', 'company', 'stage']
export const ORDERS: Order[] = ['asc', 'desc']

export const SORT_COLUMNS: Record<Sort, SortColumn> = {
    moved: {
        label: 'Moved',
        hint: 'Last stage change or archiving',
        firstOrder: 'desc',
        orderLabels: { asc: 'Oldest first', desc: 'Newest first' },
        compare: (a, b) => -newestFirst(a, b),
    },
    company: {
        label: 'Company',
        hint: 'By company name',
        firstOrder: 'asc',
        orderLabels: { asc: 'A to Z', desc: 'Z to A' },
        compare: (a, b) => a.posting.company.localeCompare(b.posting.company, 'ja'),
    },
    stage: {
        label: 'Stage',
        hint: 'Saved through Offer',
        firstOrder: 'asc',
        orderLabels: { asc: 'Saved first', desc: 'Offer first' },
        compare: (a, b) => STAGES.indexOf(a.stage) - STAGES.indexOf(b.stage),
    },
}

export const SORT_OPTIONS = SORTS.map((sort) => ({ value: sort, label: SORT_COLUMNS[sort].label, hint: SORT_COLUMNS[sort].hint }))

export const LABELS: Record<Filter, string> = {
    all: 'All',
    saved: 'Saved',
    applied: 'Applied',
    interviewing: 'Interviewing',
    offer: 'Offer',
    archived: 'Archived',
}

function readOneOf<T extends string>(params: URLSearchParams, key: string, values: T[], fallback: T): T {
    const value = params.get(key)
    return values.find((known) => known === value) ?? fallback
}

export function readTrackerView(params: URLSearchParams): TrackerView {
    const sort = readOneOf(params, 'sort', SORTS, 'moved')
    return {
        stage: readOneOf(params, 'stage', FILTERS, 'all'),
        sort,
        order: readOneOf(params, 'order', ORDERS, SORT_COLUMNS[sort].firstOrder),
    }
}

export function trackerViewToSearch(view: TrackerView): string {
    const params = new URLSearchParams()
    if (view.stage !== 'all') params.set('stage', view.stage)
    if (view.sort !== 'moved') params.set('sort', view.sort)
    if (view.order !== SORT_COLUMNS[view.sort].firstOrder) params.set('order', view.order)
    return params.toString()
}

export function pickSort(view: TrackerView, sort: Sort): TrackerView {
    return sort === view.sort ? view : { ...view, sort, order: SORT_COLUMNS[sort].firstOrder }
}

export function clickSort(view: TrackerView, sort: Sort): TrackerView {
    return sort === view.sort ? flipOrder(view) : pickSort(view, sort)
}

export function flipOrder(view: TrackerView): TrackerView {
    return { ...view, order: view.order === 'asc' ? 'desc' : 'asc' }
}

export function orderLabel(sort: Sort, order: Order): string {
    return SORT_COLUMNS[sort].orderLabels[order]
}

export function matchesFilter(row: Staged, filter: Filter): boolean {
    if (filter === 'archived') return row.archived
    return !row.archived && (filter === 'all' || row.stage === filter)
}

function newestFirst(a: TrackerRow, b: TrackerRow): number {
    return Date.parse(b.moved_at) - Date.parse(a.moved_at) || b.id - a.id
}

export function viewRows<T extends TrackerRow>(rows: T[], view: TrackerView): T[] {
    const sign = view.order === 'asc' ? 1 : -1
    const { compare } = SORT_COLUMNS[view.sort]
    return rows.filter((row) => matchesFilter(row, view.stage)).sort((a, b) => sign * compare(a, b) || newestFirst(a, b))
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
