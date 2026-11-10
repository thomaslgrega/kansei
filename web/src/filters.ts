import { type JapaneseChoice, type JapaneseFacts, japaneseRequirement, passesJapanese, readJapaneseChoice } from './japanese'

export type Filters = { japanese: JapaneseChoice; showSales: boolean }

export const DEFAULT_FILTERS: Filters = { japanese: 'any', showSales: false }

type FilterableRow = { facts: JapaneseFacts; sales_or_support: boolean }

export function readFilters(params: URLSearchParams): Filters {
    return { japanese: readJapaneseChoice(params.get('japanese')), showSales: params.get('sales') === '1' }
}

export function filtersToSearch(filters: Filters): string {
    const params = new URLSearchParams()
    if (filters.japanese !== 'any') params.set('japanese', filters.japanese)
    if (filters.showSales) params.set('sales', '1')
    return params.toString()
}

export function filterRows<R extends FilterableRow>(rows: R[], filters: Filters): { visible: R[]; hiddenSales: number } {
    const passing = rows.filter(({ facts }) => passesJapanese(japaneseRequirement(facts), filters.japanese))
    const hiddenSales = passing.filter((row) => row.sales_or_support).length
    const visible = filters.showSales ? passing : passing.filter((row) => !row.sales_or_support)
    return { visible, hiddenSales }
}
