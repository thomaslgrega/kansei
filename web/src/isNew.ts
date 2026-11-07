// A posting is New for this long after kansei first saw it. Two days rather than one, so a
// visitor who skips a day still sees everything they missed.
//
// The clock runs from first_seen_at, not from when the company published the posting. A board
// added today shows its whole backlog as New, even postings that are months old. That is
// intended: kansei's users have never seen them.
const NEW_FOR_MS = 2 * 24 * 60 * 60 * 1000

export function isNew(firstSeenAt: string, now: number): boolean {
    return now - new Date(firstSeenAt).getTime() < NEW_FOR_MS
}
