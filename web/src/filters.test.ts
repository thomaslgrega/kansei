import { expect, test } from 'vitest'
import { filtersToSearch, readFilters } from './filters'

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
