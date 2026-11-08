// A newly added board's whole backlog counts as New on purpose: users have never seen it.
const NEW_FOR_MS = 2 * 24 * 60 * 60 * 1000

export function isNew(firstSeenAt: string, now: number): boolean {
    return now - new Date(firstSeenAt).getTime() < NEW_FOR_MS
}
