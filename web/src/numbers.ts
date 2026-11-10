import { DEFAULT_FILTERS, filterRows } from './filters'
import { firstSeenAgo } from './firstSeen'
import type { JapaneseFacts } from './japanese'

type NumbersRow = {
    posting: { source: string; last_seen_at: string }
    facts: JapaneseFacts
    sales_or_support: boolean
}

export type Numbers = { postings: number; updatedAt: string | null }

const MINUTE_MS = 60 * 1000

const ago = new Intl.RelativeTimeFormat('en', { numeric: 'always' })

export function siteNumbers(rows: NumbersRow[]): Numbers {
    let updatedAt: string | null = null
    for (const { posting } of rows) {
        if (posting.source === 'url') continue
        if (updatedAt === null || Date.parse(posting.last_seen_at) > Date.parse(updatedAt)) updatedAt = posting.last_seen_at
    }
    return { postings: filterRows(rows, DEFAULT_FILTERS).visible.length, updatedAt }
}

export function updatedAgo(updatedAt: string, now: number): string {
    const minutes = Math.max(0, Math.floor((now - Date.parse(updatedAt)) / MINUTE_MS))
    if (minutes < 1) return 'just now'
    if (minutes < 60) return ago.format(-minutes, 'minute')
    if (minutes < 24 * 60) return ago.format(-Math.floor(minutes / 60), 'hour')
    return firstSeenAgo(updatedAt, now)
}

export function numbersLine({ postings, updatedAt }: Numbers, now: number): string {
    const count = `${postings} ${postings === 1 ? 'posting' : 'postings'}`
    return updatedAt === null ? count : `${count} · updated ${updatedAgo(updatedAt, now)}`
}
