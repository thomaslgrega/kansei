import { expect, test } from 'vitest'
import { isNew } from './isNew'

test('a posting is New for less than two days after kansei first saw it', () => {
    const now = Date.parse('2026-11-08T12:00:00Z')
    const firstSeen = [
        '2026-11-08T11:00:00+00:00', // an hour ago
        '2026-11-06T12:00:01+00:00', // one second short of two days
        '2026-11-06T12:00:00+00:00', // exactly two days
        '2026-10-01T00:00:00+00:00', // weeks ago
    ]

    expect(firstSeen.map((value) => isNew(value, now))).toEqual([true, true, false, false])
})

test('reads the API timestamp format, with microseconds and an offset', () => {
    const now = Date.parse('2026-11-08T12:00:00Z')
    const firstSeen = [
        '2026-11-06T21:00:00.500000+09:00', // half a second short of two days
        '2026-11-06T20:59:59.500000+09:00', // half a second past two days
    ]

    expect(firstSeen.map((value) => isNew(value, now))).toEqual([true, false])
})
