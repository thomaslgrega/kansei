import type { Move, Tracked } from './Tracker'
import { asksBeforeUntrack } from './trackerView'

export type TrackControls = {
    ids: Set<number>
    pending: Set<number>
    asksBeforeUntrackingPosting: (postingId: number) => boolean
    track: (postingId: number) => void
    untrack: (postingId: number) => void
}

function rowFor(tracked: Tracked[], postingId: number): Tracked | undefined {
    return tracked.find((row) => row.posting.id === postingId)
}

export function trackedRowId(tracked: Tracked[], postingId: number): number | null {
    return rowFor(tracked, postingId)?.id ?? null
}

export function asksBeforeUntrackingPosting(tracked: Tracked[], postingId: number): boolean {
    const row = rowFor(tracked, postingId)
    return row !== undefined && asksBeforeUntrack(row)
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
