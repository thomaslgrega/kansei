export type Board = { source: string; token: string; company: string; logo_url: string | null }

export type FollowControls = {
    keys: Set<string>
    pending: Set<string>
    follow: (source: string, token: string) => void
    unfollow: (source: string, token: string) => void
}

export function boardKey(board: { source: string; token: string }): string {
    return `${board.source}:${board.token}`
}

export function parseBoardKey(key: string): { source: string; token: string } {
    const colon = key.indexOf(':')
    return { source: key.slice(0, colon), token: key.slice(colon + 1) }
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
