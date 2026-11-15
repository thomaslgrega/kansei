import { parseBoardKey } from './boards'
import { type JapaneseChoice, readJapaneseChoice } from './japanese'
import { readSpecialties, type Selected, specialtiesParam } from './specialty'

export type Filters = { japanese: JapaneseChoice; specialties: Selected; board: string | null; query: string }

export function readFilters(params: URLSearchParams, followed: ReadonlySet<string> = new Set()): Filters {
    const company = params.get('company')
    return {
        japanese: readJapaneseChoice(params.get('japanese')),
        specialties: readSpecialties(params.get('specialty')),
        board: company !== null && followed.has(company) ? company : null,
        query: params.get('q')?.trim() ?? '',
    }
}

function filterParams(filters: Filters, page: number): URLSearchParams {
    const params = new URLSearchParams()
    if (filters.query !== '') params.set('q', filters.query)
    if (filters.japanese !== 'any') params.set('japanese', filters.japanese)
    const specialty = specialtiesParam(filters.specialties)
    if (specialty !== null) params.set('specialty', specialty)
    if (filters.board !== null) params.set('company', filters.board)
    if (page !== 1) params.set('page', String(page))
    return params
}

export function toSearch(params: URLSearchParams): string {
    // Neither a comma nor a colon separates anything in a query string, so leaving them plain changes no value.
    return params.toString().replaceAll('%2C', ',').replaceAll('%3A', ':')
}

export function filtersToSearch(filters: Filters, page = 1): string {
    return toSearch(filterParams(filters, page))
}

export function querySearch(filters: Filters, typed: string): string {
    return filtersToSearch({ ...filters, query: typed.trim() })
}

export function boardClickSearch(filters: Filters, clicked: string, managing: boolean): string | null {
    if (managing) return null
    return filtersToSearch({ ...filters, board: filters.board === clicked ? null : clicked })
}

export function droppedBoardSearch(params: URLSearchParams, followed: ReadonlySet<string>): string | null {
    const filters = readFilters(params, followed)
    return params.has('company') && filters.board === null ? filtersToSearch(filters) : null
}

// Every chip shows its count, so the company picked to filter the postings is left out.
export function newCountsUrl(filters: Filters): string {
    const search = filtersToSearch({ ...filters, board: null, query: '' })
    return search ? `/api/me/follows/new?${search}` : '/api/me/follows/new'
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
