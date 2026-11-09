export type Board = { source: string; token: string; company: string }

export function boardKey(board: { source: string; token: string }): string {
    return `${board.source}:${board.token}`
}

export function followsKey(followed: Set<string>): string {
    return [...followed].sort().join(' ')
}

export function latestOnly<T>(load: () => Promise<T>): () => Promise<T | undefined> {
    let latest = 0
    return async () => {
        const call = ++latest
        const result = await load()
        return call === latest ? result : undefined
    }
}
