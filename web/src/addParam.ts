import { toSearch } from './filters'

export function readAddParam(params: URLSearchParams): string | null {
    return params.get('add')?.trim() || null
}

export function searchWithoutAdd(params: URLSearchParams): string {
    const kept = new URLSearchParams(params)
    kept.delete('add')
    return toSearch(kept)
}
