import { type JapaneseChoice, japaneseChoice } from './japanese'

export type Filters = { japanese: JapaneseChoice; showSales: boolean }

export function readFilters(params: URLSearchParams): Filters {
    return { japanese: japaneseChoice(params.get('japanese')), showSales: params.get('sales') === '1' }
}

export function filtersToSearch(filters: Filters): string {
    const params = new URLSearchParams()
    if (filters.japanese !== 'any') params.set('japanese', filters.japanese)
    if (filters.showSales) params.set('sales', '1')
    return params.toString()
}
