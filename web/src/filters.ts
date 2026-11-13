import { type JapaneseChoice, readJapaneseChoice } from './japanese'
import { readSpecialties, type Selected, specialtiesParam } from './specialty'

export type Filters = { japanese: JapaneseChoice; specialties: Selected }

export function readFilters(params: URLSearchParams): Filters {
    return { japanese: readJapaneseChoice(params.get('japanese')), specialties: readSpecialties(params.get('specialty')) }
}

function filterParams(filters: Filters, page: number): URLSearchParams {
    const params = new URLSearchParams()
    if (filters.japanese !== 'any') params.set('japanese', filters.japanese)
    const specialty = specialtiesParam(filters.specialties)
    if (specialty !== null) params.set('specialty', specialty)
    if (page !== 1) params.set('page', String(page))
    return params
}

function toSearch(params: URLSearchParams): string {
    // Every value comes from a fixed list, so a plain comma can't be confused for one inside a value.
    return params.toString().replaceAll('%2C', ',')
}

export function filtersToSearch(filters: Filters, page = 1): string {
    return toSearch(filterParams(filters, page))
}

export function postingsUrl(followingOnly: boolean, filters: Filters, page = 1): string {
    const params = new URLSearchParams()
    if (followingOnly) params.set('following', 'true')
    filterParams(filters, page).forEach((value, key) => params.set(key, value))
    const search = toSearch(params)
    return search ? `/api/postings?${search}` : '/api/postings'
}
