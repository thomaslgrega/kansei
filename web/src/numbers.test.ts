import { expect, test } from 'vitest'
import { numbersLine, siteNumbers, updatedAgo } from './numbers'

const noJapanese = { japanese_required: 'not_required', japanese_level: '', jlpt: '' } as const
const nativeJapanese = { japanese_required: 'required', japanese_level: 'native', jlpt: '' } as const

function row(source: string, lastSeenAt: string, facts: typeof noJapanese | typeof nativeJapanese, salesOrSupport = false) {
    return { posting: { source, last_seen_at: lastSeenAt }, facts, sales_or_support: salesOrSupport }
}

test('counts the postings the default filters show and dates them by the newest board posting', () => {
    const rows = [
        row('greenhouse', '2026-11-10T03:00:00+00:00', noJapanese),
        row('lever', '2026-11-10T13:30:00+09:00', nativeJapanese),
        row('ashby', '2026-11-10T05:00:00+00:00', noJapanese, true),
        row('url', '2026-11-10T09:00:00+00:00', noJapanese),
    ]

    expect(siteNumbers(rows)).toEqual({ postings: 3, updatedAt: '2026-11-10T05:00:00+00:00' })
})

test('with no board postings there is no updated time', () => {
    expect(siteNumbers([row('url', '2026-11-10T09:00:00+00:00', noJapanese)])).toEqual({
        postings: 1,
        updatedAt: null,
    })
    expect(siteNumbers([])).toEqual({ postings: 0, updatedAt: null })
})

test('updated reads in minutes, then hours, then days', () => {
    const now = Date.parse('2026-11-10T12:00:00Z')
    const updated = [
        '2026-11-10T12:00:05+00:00', // just ahead of the browser clock
        '2026-11-10T11:59:30+00:00', // 30 seconds
        '2026-11-10T11:59:00+00:00', // a minute
        '2026-11-10T11:01:00+00:00', // 59 minutes
        '2026-11-10T11:00:00+00:00', // an hour
        '2026-11-10T00:00:01.500000+00:00', // just short of 12 hours
        '2026-11-09T12:00:01+00:00', // one second short of a day
        '2026-11-09T12:00:00+00:00', // a day
        '2026-11-07T12:00:00+00:00', // three days
    ]

    expect(updated.map((value) => updatedAgo(value, now))).toEqual([
        'just now',
        'just now',
        '1 minute ago',
        '59 minutes ago',
        '1 hour ago',
        '11 hours ago',
        '23 hours ago',
        'yesterday',
        '3 days ago',
    ])
})

test('the numbers line names the count and when kansei last read the boards', () => {
    const now = Date.parse('2026-11-10T12:00:00Z')
    const lines = [
        numbersLine({ postings: 377, updatedAt: '2026-11-10T09:00:00+00:00' }, now),
        numbersLine({ postings: 1, updatedAt: '2026-11-10T09:00:00+00:00' }, now),
        numbersLine({ postings: 0, updatedAt: null }, now),
    ]

    expect(lines).toEqual(['377 postings · updated 3 hours ago', '1 posting · updated 3 hours ago', '0 postings'])
})
