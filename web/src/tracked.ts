import type { Tracked } from './TrackedPostings'

export function trackedRowId(tracked: Tracked[], postingId: number): number | null {
    return tracked.find((row) => row.posting.id === postingId)?.id ?? null
}

export function withoutPosting(tracked: Tracked[], postingId: number): Tracked[] {
    return tracked.filter((row) => row.posting.id !== postingId)
}
