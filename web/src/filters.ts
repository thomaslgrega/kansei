import { parseBoardKey } from './boards'
import { type JapaneseChoice, readJapaneseChoice } from './japanese'
import { readSpecialties, type Selected, specialtiesParam } from './specialty'

export type Filters = { japanese: JapaneseChoice; specialties: Selected; board: string | null }

export function readFilters(params: URLSearchParams, followed: ReadonlySet<string> = new Set()): Filters {
    const company = params.get('company')
    return {
        japanese: readJapaneseChoice(params.get('japanese')),
        specialties: readSpecialties(params.get('specialty')),
        board: company !== null && followed.has(company) ? company : null,
    }
}

function filterParams(filters: Filters, page: number): URLSearchParams {
    const params = new URLSearchParams()
    if (filters.japanese !== 'any') params.set('japanese', filters.japanese)
    const specialty = specialtiesParam(filters.specialties)
    if (specialty !== null) params.set('specialty', specialty)
    if (filters.board !== null) params.set('company', filters.board)
    if (page !== 1) params.set('page', String(page))
    return params
}

function toSearch(params: URLSearchParams): string {
    // Values are fixed words or board slugs, so neither a plain comma nor a colon can be confused for one inside a value.
    return params.toString().replaceAll('%2C', ',').replaceAll('%3A', ':')
}

export function filtersToSearch(filters: Filters, page = 1): string {
    return toSearch(filterParams(filters, page))
}

export function boardClickSearch(filters: Filters, clicked: string, managing: boolean): string | null {
    if (managing) return null
    return filtersToSearch({ ...filters, board: filters.board === clicked ? null : clicked })
}

export function droppedBoardSearch(params: URLSearchParams, followed: ReadonlySet<string>): string | null {
    const filters = readFilters(params, followed)
    return params.has('company') && filters.board === null ? filtersToSearch(filters) : null
}

export function postingsUrl(followingOnly: boolean, filters: Filters, page = 1): string {
    const params = new URLSearchParams()
    if (followingOnly) params.set('following', 'true')
    if (filters.board !== null) {
        const { source, token } = parseBoardKey(filters.board)
        params.set('source', source)
        params.set('token', token)
    }
    filterParams({ ...filters, board: null }, page).forEach((value, key) => params.set(key, value))
    const search = toSearch(params)
    return search ? `/api/postings?${search}` : '/api/postings'
}
