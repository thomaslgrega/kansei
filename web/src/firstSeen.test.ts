import { expect, test } from 'vitest'
import { firstSeenAgo } from './firstSeen'

test('first seen reads in days for a month, then in months, then in years', () => {
    const now = Date.parse('2026-11-08T12:00:00Z')
    const firstSeen = [
        '2026-11-08T11:00:00+00:00', // an hour ago
        '2026-11-07T12:00:01+00:00', // one second short of a day
        '2026-11-07T12:00:00+00:00', // a day
        '2026-11-06T09:00:00+00:00', // two days and three hours
        '2026-10-10T12:00:00+00:00', // 29 days
        '2026-10-09T12:00:00+00:00', // 30 days
        '2026-08-08T12:00:00+00:00', // 92 days
        '2025-11-08T12:00:00+00:00', // 365 days
        '2023-11-08T12:00:00+00:00', // three years
    ]

    expect(firstSeen.map((value) => firstSeenAgo(value, now))).toEqual([
        'today',
        'today',
        'yesterday',
        '2 days ago',
        '29 days ago',
        '1 month ago',
        '3 months ago',
        '1 year ago',
        '3 years ago',
    ])
})

test('a first seen just ahead of the browser clock reads today', () => {
    const now = Date.parse('2026-11-08T12:00:00Z')

    expect(firstSeenAgo('2026-11-08T12:00:05+00:00', now)).toEqual('today')
})

test('reads the API timestamp format, with microseconds and an offset', () => {
    const now = Date.parse('2026-11-08T12:00:00Z')

    expect(firstSeenAgo('2026-11-07T21:00:00.500000+09:00', now)).toEqual('today')
})
