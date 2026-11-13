import { expect, test } from 'vitest'
import { applyMove, asksBeforeUntrackingPosting, trackedRowId, withoutPosting, withRow } from './tracked'
import type { Tracked } from './Tracker'

function row(id: number, postingId: number): Tracked {
    return {
        id,
        stage: 'saved',
        archived: false,
        note: '',
        tracked_at: '',
        moved_at: '',
        posting: {
            id: postingId,
            url: '',
            source: 'greenhouse',
            token: 'acme',
            company: 'Acme',
            logo_url: null,
            has_board: true,
            title: `Posting ${postingId}`,
            location: 'Tokyo',
            first_seen_at: '',
            last_seen_at: '',
            listed: true,
        },
        facts: null,
        japanese_requirement: null,
    }
}

test('the tracked row id is found by posting id, not by row id', () => {
    const tracked = [row(7, 3), row(3, 9)]

    expect([trackedRowId(tracked, 3), trackedRowId(tracked, 9), trackedRowId(tracked, 7)]).toEqual([7, 3, null])
})

test('removing a posting keeps the other rows in order', () => {
    const tracked = [row(1, 10), row(2, 20), row(3, 30)]

    expect(withoutPosting(tracked, 20)).toEqual([row(1, 10), row(3, 30)])
})

test('removing a posting that is not tracked changes nothing', () => {
    const tracked = [row(1, 10), row(2, 20)]

    expect(withoutPosting(tracked, 1)).toEqual([row(1, 10), row(2, 20)])
})

test('a returned row replaces the one with its id and keeps its place', () => {
    const tracked = [row(1, 10), row(2, 20), row(3, 30)]
    const moved = { ...row(2, 20), stage: 'offer' as const, archived: true }

    expect(withRow(tracked, moved)).toEqual([row(1, 10), moved, row(3, 30)])
})

test('a picked move shows at once: a stage unarchives, archiving keeps the stage', () => {
    const archived = { ...row(1, 10), stage: 'interviewing' as const, archived: true }

    expect([applyMove(archived, { stage: 'offer' }), applyMove(row(2, 20), { archived: true })]).toEqual([
        { ...archived, stage: 'offer', archived: false },
        { ...row(2, 20), archived: true },
    ])
})

test('untracking by posting id asks by that posting row, and an untracked posting never asks', () => {
    const tracked = [
        row(1, 10),
        { ...row(2, 20), stage: 'applied' as const },
        { ...row(3, 30), note: 'Ask about visa' },
        { ...row(4, 40), archived: true },
    ]

    expect([10, 20, 30, 40, 50].map((postingId) => asksBeforeUntrackingPosting(tracked, postingId))).toEqual([
        false,
        true,
        true,
        true,
        false,
    ])
})
