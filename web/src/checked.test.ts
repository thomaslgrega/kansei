import { expect, test } from 'vitest'
import { checkedAgo, lastChecked } from './checked'

function row(source: string, lastSeenAt: string, salesOrSupport = false) {
    return { posting: { source, last_seen_at: lastSeenAt }, sales_or_support: salesOrSupport }
}

test('checked is the newest board posting, counting sales roles and ignoring pasted postings', () => {
    const rows = [
        row('greenhouse', '2026-11-10T03:00:00+00:00'),
        row('lever', '2026-11-10T13:30:00+09:00'),
        row('ashby', '2026-11-10T05:00:00+00:00', true),
        row('url', '2026-11-10T09:00:00+00:00'),
    ]

    expect(lastChecked(rows)).toEqual('2026-11-10T05:00:00+00:00')
})

test('with no board postings there is no checked time', () => {
    expect([lastChecked([row('url', '2026-11-10T09:00:00+00:00')]), lastChecked([])]).toEqual([null, null])
})

test('checked reads in minutes, then hours, then days', () => {
    const now = Date.parse('2026-11-10T12:00:00Z')
    const checked = [
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

    expect(checked.map((value) => checkedAgo(value, now))).toEqual([
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
