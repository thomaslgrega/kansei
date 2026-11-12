import { type JapaneseChoice, readJapaneseChoice } from './japanese'

export type Filters = { japanese: JapaneseChoice; showSales: boolean }

export function readFilters(params: URLSearchParams): Filters {
    return { japanese: readJapaneseChoice(params.get('japanese')), showSales: params.get('sales') === '1' }
}

export function filtersToSearch(filters: Filters): string {
    const params = new URLSearchParams()
    if (filters.japanese !== 'any') params.set('japanese', filters.japanese)
    if (filters.showSales) params.set('sales', '1')
    return params.toString()
}

export function postingsUrl(followingOnly: boolean, japanese: JapaneseChoice): string {
    const params = new URLSearchParams()
    if (followingOnly) params.set('following', 'true')
    if (japanese !== 'any') params.set('japanese', japanese)
    const search = params.toString()
    return search ? `/api/postings?${search}` : '/api/postings'
}
