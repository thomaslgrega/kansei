const DAY_MS = 24 * 60 * 60 * 1000

const inDays = new Intl.RelativeTimeFormat('en', { numeric: 'auto' })
const inMonthsOrYears = new Intl.RelativeTimeFormat('en', { numeric: 'always' })

export function firstSeenAgo(firstSeenAt: string, now: number): string {
    // A browser clock behind the server's would otherwise say "tomorrow".
    const elapsedDays = Math.max(0, Math.floor((now - new Date(firstSeenAt).getTime()) / DAY_MS))
    if (elapsedDays < 30) return inDays.format(-elapsedDays, 'day')
    if (elapsedDays < 365) return inMonthsOrYears.format(-Math.floor(elapsedDays / 30), 'month')
    return inMonthsOrYears.format(-Math.floor(elapsedDays / 365), 'year')
}
