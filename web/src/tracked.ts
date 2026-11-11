import type { Tracked } from './Tracker'

export type TrackControls = {
    ids: Set<number>
    pending: Set<number>
    track: (postingId: number) => void
    untrack: (postingId: number) => void
}

export function trackedRowId(tracked: Tracked[], postingId: number): number | null {
    return tracked.find((row) => row.posting.id === postingId)?.id ?? null
}

export function withoutPosting(tracked: Tracked[], postingId: number): Tracked[] {
    return tracked.filter((row) => row.posting.id !== postingId)
}
