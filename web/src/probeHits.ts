import { boardKey } from './boards'

export type Hit = {
    source: string
    token: string
    company: string | null
    titles: string[]
    candidates: number
    state: 'not_on_kansei' | 'on_kansei' | 'removed'
    following: boolean
    logo_url: string | null
}

export type HitAction = 'add' | 'follow' | 'following' | 'removed'

export function hitAction(hit: Hit, followed: Set<string>): HitAction {
    if (hit.state === 'removed') return 'removed'
    if (followed.has(boardKey(hit))) return 'following'
    return hit.state === 'not_on_kansei' ? 'add' : 'follow'
}

export function candidateCountLabel(candidates: number): string {
    if (candidates === 0) return 'No Japan engineering jobs right now'
    return `${candidates} Japan engineering ${candidates === 1 ? 'job' : 'jobs'}`
}

export function hitName(hit: Hit): string {
    return hit.company ?? hit.token
}

export function followedNotice(hit: Hit): string {
    const name = hitName(hit)
    return hit.state === 'not_on_kansei' ? `Added ${name}. Its jobs will appear after the next update.` : `Following ${name}.`
}
