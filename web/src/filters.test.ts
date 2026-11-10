import { expect, test } from 'vitest'
import { DEFAULT_FILTERS, type Filters, filterRows, filtersToSearch, readFilters } from './filters'

test('reads both filters from the query string', () => {
    const searches = ['?japanese=basic&sales=1', '?japanese=native', '?sales=1', '']

    expect(searches.map((search) => readFilters(new URLSearchParams(search)))).toEqual([
        { japanese: 'basic', showSales: true },
        { japanese: 'native', showSales: false },
        { japanese: 'any', showSales: true },
        { japanese: 'any', showSales: false },
    ])
})

test('an unknown value reads as the default', () => {
    const searches = ['?japanese=fluent&sales=yes', '?japanese=any&sales=0', '?japanese=toString']

    expect(searches.map((search) => readFilters(new URLSearchParams(search)))).toEqual([
        { japanese: 'any', showSales: false },
        { japanese: 'any', showSales: false },
        { japanese: 'any', showSales: false },
    ])
})

test('writes the filters to the query string and leaves defaults out', () => {
    const searches = [
        filtersToSearch({ japanese: 'conversational', showSales: true }),
        filtersToSearch({ japanese: 'none', showSales: false }),
        filtersToSearch({ japanese: 'any', showSales: true }),
        filtersToSearch({ japanese: 'any', showSales: false }),
    ]

    expect(searches).toEqual(['japanese=conversational&sales=1', 'japanese=none', 'sales=1', ''])
})

function facts(japanese_required: 'required' | 'not_required', japanese_level: string) {
    return { japanese_required, japanese_level, jlpt: '' }
}

test('shows the rows within the chosen Japanese level and counts the sales roles it hides', () => {
    const rows = [
        { id: 1, facts: facts('not_required', ''), sales_or_support: false },
        { id: 2, facts: facts('required', 'business'), sales_or_support: false },
        { id: 3, facts: facts('not_required', ''), sales_or_support: true },
        { id: 4, facts: facts('required', 'business'), sales_or_support: true },
    ]
    const choices: Filters[] = [
        DEFAULT_FILTERS,
        { japanese: 'conversational', showSales: false },
        { japanese: 'conversational', showSales: true },
    ]

    expect(choices.map((filters) => {
        const { visible, hiddenSales } = filterRows(rows, filters)
        return { visible: visible.map((row) => row.id), hiddenSales }
    })).toEqual([
        { visible: [1, 2], hiddenSales: 2 },
        { visible: [1], hiddenSales: 1 },
        { visible: [1, 3], hiddenSales: 1 },
    ])
})

test('the default filters are the ones an empty query string reads as', () => {
    expect(readFilters(new URLSearchParams(''))).toEqual(DEFAULT_FILTERS)
})
