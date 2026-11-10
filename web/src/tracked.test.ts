import { expect, test } from 'vitest'
import { trackedRowId, withoutPosting } from './tracked'
import type { Tracked } from './TrackedPostings'

function row(id: number, postingId: number): Tracked {
    return {
        id,
        status: 'saved',
        note: '',
        posting: { id: postingId, title: `Posting ${postingId}`, url: '', location: 'Tokyo', first_seen_at: '', listed: true },
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
