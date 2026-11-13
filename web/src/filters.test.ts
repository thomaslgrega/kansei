import { expect, test } from 'vitest'
import { type Filters, filtersToSearch, postingsUrl, readFilters } from './filters'

test('reads both filters from the query string and ignores sales', () => {
    const searches = ['?japanese=basic&specialty=backend,ml', '?japanese=native', '?specialty=', '?sales=1', '']

    expect(searches.map((search) => readFilters(new URLSearchParams(search)))).toEqual([
        { japanese: 'basic', specialties: ['backend', 'ml'] },
        { japanese: 'native', specialties: null },
        { japanese: 'any', specialties: [] },
        { japanese: 'any', specialties: null },
        { japanese: 'any', specialties: null },
    ])
})

test('an unknown value reads as the default', () => {
    const searches = ['?japanese=fluent', '?japanese=any', '?japanese=toString']

    expect(searches.map((search) => readFilters(new URLSearchParams(search)))).toEqual([
        { japanese: 'any', specialties: null },
        { japanese: 'any', specialties: null },
        { japanese: 'any', specialties: null },
    ])
})

test('writes the filters to the query string with plain commas and leaves defaults out', () => {
    const searches = [
        filtersToSearch({ japanese: 'conversational', specialties: ['backend', 'ml'] }),
        filtersToSearch({ japanese: 'none', specialties: null }),
        filtersToSearch({ japanese: 'any', specialties: [] }),
        filtersToSearch({ japanese: 'any', specialties: null }),
    ]

    expect(searches).toEqual(['japanese=conversational&specialty=backend,ml', 'japanese=none', 'specialty=', ''])
})

test('a changed filter drops sales and unknown specialties from the URL', () => {
    const filters = readFilters(new URLSearchParams('?sales=1&specialty=bogus,ml,backend'))

    expect(filtersToSearch({ ...filters, japanese: 'basic' })).toEqual('japanese=basic&specialty=backend,ml')
})

test('the postings URL asks for followed boards, My Japanese and Specialty, and leaves defaults out', () => {
    const urls = [
        postingsUrl(false, { japanese: 'any', specialties: null }),
        postingsUrl(true, { japanese: 'any', specialties: null }),
        postingsUrl(false, { japanese: 'none', specialties: [] }),
        postingsUrl(true, { japanese: 'business', specialties: ['backend', 'other'] }),
    ]

    expect(urls).toEqual([
        '/api/postings',
        '/api/postings?following=true',
        '/api/postings?japanese=none&specialty=',
        '/api/postings?following=true&japanese=business&specialty=backend,other',
    ])
})

test('the page goes after the filters in both URLs, and page 1 is left out', () => {
    const filters: Filters = { japanese: 'basic', specialties: ['ml'] }

    expect([
        filtersToSearch(filters, 3),
        filtersToSearch(filters, 1),
        filtersToSearch({ japanese: 'any', specialties: null }, 2),
        postingsUrl(true, filters, 3),
        postingsUrl(false, { japanese: 'any', specialties: null }, 2),
        postingsUrl(false, filters, 1),
    ]).toEqual([
        'japanese=basic&specialty=ml&page=3',
        'japanese=basic&specialty=ml',
        'page=2',
        '/api/postings?following=true&japanese=basic&specialty=ml&page=3',
        '/api/postings?page=2',
        '/api/postings?japanese=basic&specialty=ml',
    ])
})
