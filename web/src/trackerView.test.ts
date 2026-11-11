import { expect, test } from 'vitest'
import {
    archivedOptionLabel,
    asksBeforeUntrack,
    clickSort,
    disabledFilters,
    emptyMessage,
    type Filter,
    FILTERS,
    filterCounts,
    flipOrder,
    inOrder,
    type Order,
    orderLabel,
    pickSort,
    readTrackerView,
    type Sort,
    SORTS,
    type Stage,
    type TrackerView,
    trackerViewToSearch,
    viewRows,
} from './trackerView'

type Row = { id: number; stage: Stage; archived: boolean; moved_at: string; posting: { company: string } }

function row(id: number, stage: Stage, archived: boolean, moved_at: string, company = 'Acme'): Row {
    return { id, stage, archived, moved_at, posting: { company } }
}

function view(stage: Filter, sort: Sort = 'moved', order: Order = 'desc'): TrackerView {
    return { stage, sort, order }
}

function read(search: string): TrackerView {
    return readTrackerView(new URLSearchParams(search))
}

const rows = [
    row(1, 'saved', false, '2026-11-01T09:00:00Z'),
    row(2, 'applied', false, '2026-11-05T09:00:00Z'),
    row(3, 'applied', true, '2026-11-03T09:00:00Z'),
    row(4, 'interviewing', false, '2026-11-02T09:00:00Z'),
    row(5, 'interviewing', true, '2026-11-04T09:00:00Z'),
    row(6, 'saved', false, '2026-11-06T09:00:00Z'),
]

test('reads the stage filter from the query string', () => {
    const searches = ['?stage=saved', '?stage=applied', '?stage=interviewing', '?stage=offer', '?stage=archived', '?stage=all', '']

    expect(searches.map(read)).toEqual([
        view('saved'),
        view('applied'),
        view('interviewing'),
        view('offer'),
        view('archived'),
        view('all'),
        view('all'),
    ])
})

test('an unknown stage reads as all', () => {
    const searches = ['?stage=rejected', '?stage=Saved', '?stage=toString', '?stage=']

    expect(searches.map(read)).toEqual([view('all'), view('all'), view('all'), view('all')])
})

test('writes the stage filter to the query string and leaves all out', () => {
    expect(FILTERS.map((stage) => trackerViewToSearch(view(stage)))).toEqual([
        '',
        'stage=saved',
        'stage=applied',
        'stage=interviewing',
        'stage=offer',
        'stage=archived',
    ])
})

test('each filter keeps its rows, moved newest first, and archived mixes stages', () => {
    const ids = (stage: Filter) => viewRows(rows, view(stage)).map((row) => row.id)

    expect(FILTERS.map((stage) => [stage, ids(stage)])).toEqual([
        ['all', [6, 2, 4, 1]],
        ['saved', [6, 1]],
        ['applied', [2]],
        ['interviewing', [4]],
        ['offer', []],
        ['archived', [5, 3]],
    ])
})

test('rows moved at the same moment keep the newest id first, and oldest first reverses that', () => {
    const tied = [row(1, 'saved', false, '2026-11-01T09:00:00Z'), row(3, 'saved', false, '2026-11-01T09:00:00Z'), row(2, 'saved', false, '2026-11-01T09:00:00Z')]
    const ids = (order: Order) => viewRows(tied, view('all', 'moved', order)).map((row) => row.id)

    expect([ids('desc'), ids('asc')]).toEqual([
        [3, 2, 1],
        [1, 2, 3],
    ])
})

test('reads the sort and its order from the query string', () => {
    const searches = [
        '?sort=company',
        '?sort=company&order=desc',
        '?sort=stage',
        '?sort=stage&order=desc',
        '?sort=moved',
        '?order=asc',
        '?stage=offer&sort=company&order=desc',
    ]

    expect(searches.map(read)).toEqual([
        view('all', 'company', 'asc'),
        view('all', 'company', 'desc'),
        view('all', 'stage', 'asc'),
        view('all', 'stage', 'desc'),
        view('all', 'moved', 'desc'),
        view('all', 'moved', 'asc'),
        view('offer', 'company', 'desc'),
    ])
})

test("an unknown sort reads as moved, and an unknown order as the sort's first-click direction", () => {
    const searches = ['?sort=title', '?sort=Company', '?sort=', '?sort=company&order=up', '?sort=stage&order=', '?sort=title&order=asc']

    expect(searches.map(read)).toEqual([
        view('all', 'moved', 'desc'),
        view('all', 'moved', 'desc'),
        view('all', 'moved', 'desc'),
        view('all', 'company', 'asc'),
        view('all', 'stage', 'asc'),
        view('all', 'moved', 'asc'),
    ])
})

test("writes the sort and order, leaving out moved and each sort's first-click direction", () => {
    const views = [
        view('all', 'moved', 'desc'),
        view('all', 'moved', 'asc'),
        view('all', 'company', 'asc'),
        view('all', 'company', 'desc'),
        view('all', 'stage', 'asc'),
        view('all', 'stage', 'desc'),
        view('offer', 'stage', 'desc'),
    ]

    expect(views.map(trackerViewToSearch)).toEqual([
        '',
        'order=asc',
        'sort=company',
        'sort=company&order=desc',
        'sort=stage',
        'sort=stage&order=desc',
        'stage=offer&sort=stage&order=desc',
    ])
})

test('every view reads back as written', () => {
    const views = FILTERS.flatMap((stage) => SORTS.flatMap((sort) => (['asc', 'desc'] as Order[]).map((order) => view(stage, sort, order))))

    expect(views.map((written) => read(trackerViewToSearch(written)))).toEqual(views)
})

const sortable = [
    row(1, 'saved', false, '2026-11-01T09:00:00Z', 'Mercari'),
    row(2, 'applied', false, '2026-11-05T09:00:00Z', 'freee'),
    row(3, 'offer', false, '2026-11-03T09:00:00Z', 'Mercari'),
    row(4, 'saved', false, '2026-11-04T09:00:00Z', 'Sansan'),
    row(5, 'applied', false, '2026-11-02T09:00:00Z', 'Mercari'),
    row(6, 'interviewing', false, '2026-11-06T09:00:00Z', 'freee'),
]

test('each sort runs both ways, and ties stay moved newest first', () => {
    const ids = (sort: Sort, order: Order) => viewRows(sortable, view('all', sort, order)).map((row) => row.id)

    expect(SORTS.flatMap((sort) => [[sort, 'asc', ids(sort, 'asc')], [sort, 'desc', ids(sort, 'desc')]])).toEqual([
        ['moved', 'asc', [1, 5, 3, 4, 2, 6]],
        ['moved', 'desc', [6, 2, 4, 3, 5, 1]],
        ['company', 'asc', [6, 2, 3, 5, 1, 4]],
        ['company', 'desc', [4, 3, 5, 1, 6, 2]],
        ['stage', 'asc', [4, 1, 2, 5, 6, 3]],
        ['stage', 'desc', [3, 6, 2, 5, 4, 1]],
    ])
})

test('company names sort Latin first, then kana by reading, then kanji', () => {
    const companies = [
        'ビジョナル株式会社',
        'freee',
        'Mercari',
        '株式会社メルカリ',
        'SmartHR',
        'アンドパッド',
        'LINEヤフー',
        'Sansan',
        'エムスリー',
        'ab inc',
        'Zeals',
        'さくらインターネット',
    ]
    const named = companies.map((company, index) => row(index + 1, 'saved', false, '2026-11-01T09:00:00Z', company))

    expect(viewRows(named, view('all', 'company', 'asc')).map((row) => row.posting.company)).toEqual([
        'ab inc',
        'freee',
        'LINEヤフー',
        'Mercari',
        'Sansan',
        'SmartHR',
        'Zeals',
        'アンドパッド',
        'エムスリー',
        'さくらインターネット',
        'ビジョナル株式会社',
        '株式会社メルカリ',
    ])
})

test('a header click sorts a new column its first way and reverses the active one', () => {
    expect([
        clickSort(view('saved', 'moved', 'desc'), 'moved'),
        clickSort(view('saved', 'moved', 'asc'), 'moved'),
        clickSort(view('saved', 'moved', 'asc'), 'company'),
        clickSort(view('saved', 'company', 'asc'), 'company'),
        clickSort(view('saved', 'company', 'desc'), 'company'),
        clickSort(view('saved', 'company', 'desc'), 'stage'),
        clickSort(view('saved', 'stage', 'desc'), 'moved'),
    ]).toEqual([
        view('saved', 'moved', 'asc'),
        view('saved', 'moved', 'desc'),
        view('saved', 'company', 'asc'),
        view('saved', 'company', 'desc'),
        view('saved', 'company', 'asc'),
        view('saved', 'stage', 'asc'),
        view('saved', 'moved', 'desc'),
    ])
})

test('picking a sort from the menu uses its first way, and picking the active one changes nothing', () => {
    expect([
        pickSort(view('offer', 'moved', 'asc'), 'company'),
        pickSort(view('offer', 'company', 'desc'), 'stage'),
        pickSort(view('offer', 'stage', 'desc'), 'moved'),
        pickSort(view('offer', 'company', 'desc'), 'company'),
        pickSort(view('offer', 'moved', 'asc'), 'moved'),
    ]).toEqual([
        view('offer', 'company', 'asc'),
        view('offer', 'stage', 'asc'),
        view('offer', 'moved', 'desc'),
        view('offer', 'company', 'desc'),
        view('offer', 'moved', 'asc'),
    ])
})

test('the direction button reverses the order and keeps the sort', () => {
    expect([
        flipOrder(view('archived', 'moved', 'desc')),
        flipOrder(view('archived', 'company', 'asc')),
        flipOrder(view('archived', 'stage', 'desc')),
    ]).toEqual([view('archived', 'moved', 'asc'), view('archived', 'company', 'desc'), view('archived', 'stage', 'asc')])
})

test('each direction has a name', () => {
    expect(SORTS.flatMap((sort) => [orderLabel(sort, 'asc'), orderLabel(sort, 'desc')])).toEqual([
        'Oldest first',
        'Newest first',
        'A to Z',
        'Z to A',
        'Saved first',
        'Offer first',
    ])
})

test('all and the stages count unarchived rows, and archived counts the rest', () => {
    expect(filterCounts(rows)).toEqual({ all: 4, saved: 2, applied: 1, interviewing: 1, offer: 0, archived: 2 })
})

test('nothing tracked counts zero everywhere', () => {
    expect(filterCounts([])).toEqual({ all: 0, saved: 0, applied: 0, interviewing: 0, offer: 0, archived: 0 })
})

test('a filter with nothing in it is disabled unless it is the one selected', () => {
    const counts = { all: 3, saved: 0, applied: 2, interviewing: 1, offer: 0, archived: 0 }

    expect([
        disabledFilters(counts, 'all'),
        disabledFilters(counts, 'offer'),
        disabledFilters(counts, 'archived'),
        disabledFilters(filterCounts([]), 'all'),
    ]).toEqual([
        ['saved', 'offer', 'archived'],
        ['saved', 'archived'],
        ['saved', 'offer'],
        ['saved', 'applied', 'interviewing', 'offer', 'archived'],
    ])
})

test('the held order keeps its rows in place and drops untracked ones', () => {
    const current = [row(6, 'offer', false, '2026-11-10T09:00:00Z'), row(2, 'applied', true, '2026-11-09T09:00:00Z'), row(1, 'saved', false, '2026-11-01T09:00:00Z')]

    expect(inOrder([1, 4, 2, 6], current)).toEqual([
        row(1, 'saved', false, '2026-11-01T09:00:00Z'),
        row(2, 'applied', true, '2026-11-09T09:00:00Z'),
        row(6, 'offer', false, '2026-11-10T09:00:00Z'),
    ])
})

test('the archived option names the stage an archived row reached', () => {
    expect([
        archivedOptionLabel({ stage: 'applied', archived: false }),
        archivedOptionLabel({ stage: 'applied', archived: true }),
        archivedOptionLabel({ stage: 'interviewing', archived: true }),
    ]).toEqual(['Archived', 'Archived · Applied', 'Archived · Interviewing'])
})

test('an empty filter says what is missing', () => {
    expect(FILTERS.map(emptyMessage)).toEqual([
        'Nothing in progress.',
        'Nothing in Saved.',
        'Nothing in Applied.',
        'Nothing in Interviewing.',
        'Nothing in Offer.',
        'Nothing archived.',
    ])
})

test('untracking asks first unless the posting is saved, unarchived and has no note', () => {
    const cases = [
        { note: '', stage: 'saved' as const, archived: false },
        { note: 'Call on Friday', stage: 'saved' as const, archived: false },
        { note: ' \n ', stage: 'saved' as const, archived: false },
        { note: '', stage: 'applied' as const, archived: false },
        { note: '', stage: 'offer' as const, archived: false },
        { note: '', stage: 'saved' as const, archived: true },
        { note: 'Sent CV', stage: 'interviewing' as const, archived: true },
    ]

    expect(cases.map(asksBeforeUntrack)).toEqual([false, true, false, true, true, true, true])
})
