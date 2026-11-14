import { type Board, boardKey } from './boards'

export type FollowChip = { key: string; board: Board; source: string | null }

export function followChips(boards: Board[]): FollowChip[] {
    const counts = new Map<string, number>()
    for (const board of boards) {
        const name = board.company.toLowerCase()
        counts.set(name, (counts.get(name) ?? 0) + 1)
    }
    return boards.map((board) => ({
        key: boardKey(board),
        board,
        source: (counts.get(board.company.toLowerCase()) ?? 0) > 1 ? board.source : null,
    }))
}
