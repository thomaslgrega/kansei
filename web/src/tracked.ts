import type { Move, Tracked } from './Tracker'

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

export function withRow(tracked: Tracked[], updated: Tracked): Tracked[] {
    return tracked.map((row) => (row.id === updated.id ? updated : row))
}

// Shown until the PATCH answers with the row the API decided on.
export function applyMove(row: Tracked, move: Move): Tracked {
    return 'archived' in move ? { ...row, archived: true } : { ...row, stage: move.stage, archived: false }
}
