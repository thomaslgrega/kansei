import { expect, test } from 'vitest'
import {
    archivedOptionLabel,
    asksBeforeUntrack,
    disabledFilters,
    emptyMessage,
    type Filter,
    FILTERS,
    filterCounts,
    inOrder,
    readTrackerView,
    type Stage,
    trackerViewToSearch,
    viewRows,
} from './trackerView'

type Row = { id: number; stage: Stage; archived: boolean; moved_at: string }

function row(id: number, stage: Stage, archived: boolean, moved_at: string): Row {
    return { id, stage, archived, moved_at }
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

    expect(searches.map((search) => readTrackerView(new URLSearchParams(search)))).toEqual([
        { stage: 'saved' },
        { stage: 'applied' },
        { stage: 'interviewing' },
        { stage: 'offer' },
        { stage: 'archived' },
        { stage: 'all' },
        { stage: 'all' },
    ])
})

test('an unknown stage reads as all', () => {
    const searches = ['?stage=rejected', '?stage=Saved', '?stage=toString', '?stage=']

    expect(searches.map((search) => readTrackerView(new URLSearchParams(search)))).toEqual([
        { stage: 'all' },
        { stage: 'all' },
        { stage: 'all' },
        { stage: 'all' },
    ])
})

test('writes the stage filter to the query string and leaves all out', () => {
    expect(FILTERS.map((stage) => trackerViewToSearch({ stage }))).toEqual([
        '',
        'stage=saved',
        'stage=applied',
        'stage=interviewing',
        'stage=offer',
        'stage=archived',
    ])
})

test('each filter keeps its rows, moved newest first, and archived mixes stages', () => {
    const ids = (stage: Filter) => viewRows(rows, { stage }).map((row) => row.id)

    expect(FILTERS.map((stage) => [stage, ids(stage)])).toEqual([
        ['all', [6, 2, 4, 1]],
        ['saved', [6, 1]],
        ['applied', [2]],
        ['interviewing', [4]],
        ['offer', []],
        ['archived', [5, 3]],
    ])
})

test('rows moved at the same moment keep the newest id first', () => {
    const tied = [row(1, 'saved', false, '2026-11-01T09:00:00Z'), row(3, 'saved', false, '2026-11-01T09:00:00Z'), row(2, 'saved', false, '2026-11-01T09:00:00Z')]

    expect(viewRows(tied, { stage: 'all' }).map((row) => row.id)).toEqual([3, 2, 1])
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
