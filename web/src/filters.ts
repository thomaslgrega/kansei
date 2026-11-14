import { type JapaneseChoice, readJapaneseChoice } from './japanese'
import { readSpecialties, type Selected, specialtiesParam } from './specialty'

// `company` is a followed board's key, `source:token`.
export type Filters = { japanese: JapaneseChoice; specialties: Selected; company: string | null }

export function readFilters(params: URLSearchParams, followed: ReadonlySet<string> = new Set()): Filters {
    const company = params.get('company')
    return {
        japanese: readJapaneseChoice(params.get('japanese')),
        specialties: readSpecialties(params.get('specialty')),
        company: company !== null && followed.has(company) ? company : null,
    }
}

function filterParams(filters: Filters, page: number): URLSearchParams {
    const params = new URLSearchParams()
    if (filters.japanese !== 'any') params.set('japanese', filters.japanese)
    const specialty = specialtiesParam(filters.specialties)
    if (specialty !== null) params.set('specialty', specialty)
    if (filters.company !== null) params.set('company', filters.company)
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

export function companyClickSearch(filters: Filters, clicked: string, managing: boolean): string | null {
    if (managing) return null
    return filtersToSearch({ ...filters, company: filters.company === clicked ? null : clicked })
}

export function droppedCompanySearch(params: URLSearchParams, followed: ReadonlySet<string>): string | null {
    const filters = readFilters(params, followed)
    return params.has('company') && filters.company === null ? filtersToSearch(filters) : null
}

export function postingsUrl(followingOnly: boolean, filters: Filters, page = 1): string {
    const params = new URLSearchParams()
    if (followingOnly) params.set('following', 'true')
    if (filters.company !== null) {
        const colon = filters.company.indexOf(':')
        params.set('source', filters.company.slice(0, colon))
        params.set('token', filters.company.slice(colon + 1))
    }
    filterParams({ ...filters, company: null }, page).forEach((value, key) => params.set(key, value))
    const search = toSearch(params)
    return search ? `/api/postings?${search}` : '/api/postings'
}
