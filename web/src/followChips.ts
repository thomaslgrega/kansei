import { type Board, boardKey } from './boards'

export type FollowChip = { board: Board; sourceLabel: string | null; newLabel: string | null }

export function followChips(boards: Board[], newCounts: Record<string, number>, managing: boolean): FollowChip[] {
    const counts = new Map<string, number>()
    for (const board of boards) {
        const name = board.company.toLowerCase()
        counts.set(name, (counts.get(name) ?? 0) + 1)
    }
    return boards.map((board) => {
        const newCount = newCounts[boardKey(board)] ?? 0
        return {
            board,
            sourceLabel: (counts.get(board.company.toLowerCase()) ?? 0) > 1 ? board.source : null,
            newLabel: newCount > 0 && !managing ? `${newCount} new` : null,
        }
    })
}
