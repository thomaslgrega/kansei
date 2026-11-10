import { firstSeenAgo } from './firstSeen'

const MINUTE_MS = 60 * 1000

const ago = new Intl.RelativeTimeFormat('en', { numeric: 'always' })

function isPasted(posting: { source: string }): boolean {
    return posting.source === 'url'
}

export function lastChecked(rows: { posting: { source: string; last_seen_at: string } }[]): string | null {
    let checkedAt: string | null = null
    for (const { posting } of rows) {
        if (isPasted(posting)) continue
        if (checkedAt === null || Date.parse(posting.last_seen_at) > Date.parse(checkedAt)) checkedAt = posting.last_seen_at
    }
    return checkedAt
}

export function checkedAgo(checkedAt: string, now: number): string {
    const minutes = Math.max(0, Math.floor((now - Date.parse(checkedAt)) / MINUTE_MS))
    if (minutes < 1) return 'just now'
    if (minutes < 60) return ago.format(-minutes, 'minute')
    if (minutes < 24 * 60) return ago.format(-Math.floor(minutes / 60), 'hour')
    return firstSeenAgo(checkedAt, now)
}
