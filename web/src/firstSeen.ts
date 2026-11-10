const DAY_MS = 24 * 60 * 60 * 1000

const days = new Intl.RelativeTimeFormat('en', { numeric: 'auto' })
const longer = new Intl.RelativeTimeFormat('en', { numeric: 'always' })

export function firstSeenAgo(firstSeenAt: string, now: number): string {
    const elapsed = Math.floor((now - new Date(firstSeenAt).getTime()) / DAY_MS)
    if (elapsed < 30) return days.format(-elapsed, 'day')
    if (elapsed < 365) return longer.format(-Math.floor(elapsed / 30), 'month')
    return longer.format(-Math.floor(elapsed / 365), 'year')
}
