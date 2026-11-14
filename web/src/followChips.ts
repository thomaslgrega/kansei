import { type Board, boardKey } from './boards'

export type FollowChip = { board: Board; sourceLabel: string | null; newLabel: string | null }

export function followChips(boards: Board[], newCounts: Record<string, number>, managing: boolean): FollowChip[] {
    const boardsPerCompany = new Map<string, number>()
    for (const board of boards) {
        const name = board.company.toLowerCase()
        boardsPerCompany.set(name, (boardsPerCompany.get(name) ?? 0) + 1)
    }
    return boards.map((board) => {
        const newCount = newCounts[boardKey(board)] ?? 0
        return {
            board,
            sourceLabel: (boardsPerCompany.get(board.company.toLowerCase()) ?? 0) > 1 ? board.source : null,
            newLabel: newCount > 0 && !managing ? `${newCount} new` : null,
        }
    })
}

export function clampChips(chips: FollowChip[], visible: number, selected: string | null): { shown: FollowChip[]; hidden: number } {
    if (visible >= chips.length) return { shown: chips, hidden: 0 }
    const shown = chips.slice(0, visible)
    const selectedChip = chips.find((chip) => boardKey(chip.board) === selected)
    if (visible > 0 && selectedChip && !shown.includes(selectedChip)) shown[visible - 1] = selectedChip
    return { shown, hidden: chips.length - visible }
}

// tops: offsetTop of each rendered chip, then of any chips after them such as "+N more".
export function twoRowFit(tops: number[], count: number): number {
    const rows = [...new Set(tops)].sort((a, b) => a - b)
    if (rows.length <= 2) return count
    const fit = tops.slice(0, count).filter((top) => top <= rows[1]).length
    return Math.min(count - 1, fit)
}
