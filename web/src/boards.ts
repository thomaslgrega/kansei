export type Board = { source: string; token: string; company: string }

export function boardKey(board: { source: string; token: string }): string {
    return `${board.source}:${board.token}`
}
