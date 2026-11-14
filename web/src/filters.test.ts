import { expect, test } from 'vitest'
import { boardClickSearch, droppedBoardSearch, type Filters, filtersToSearch, postingsUrl, readFilters } from './filters'

test('reads both filters from the query string and ignores sales', () => {
    const searches = ['?japanese=basic&specialty=backend,ml', '?japanese=native', '?specialty=', '?sales=1', '']

    expect(searches.map((search) => readFilters(new URLSearchParams(search)))).toEqual([
        { japanese: 'basic', specialties: ['backend', 'ml'], board: null },
        { japanese: 'native', specialties: null, board: null },
        { japanese: 'any', specialties: [], board: null },
        { japanese: 'any', specialties: null, board: null },
        { japanese: 'any', specialties: null, board: null },
    ])
})

test('an unknown value reads as the default', () => {
    const searches = ['?japanese=fluent', '?japanese=any', '?japanese=toString']

    expect(searches.map((search) => readFilters(new URLSearchParams(search)))).toEqual([
        { japanese: 'any', specialties: null, board: null },
        { japanese: 'any', specialties: null, board: null },
        { japanese: 'any', specialties: null, board: null },
    ])
})

test('writes the filters to the query string with plain commas and leaves defaults out', () => {
    const searches = [
        filtersToSearch({ japanese: 'conversational', specialties: ['backend', 'ml'], board: null }),
        filtersToSearch({ japanese: 'none', specialties: null, board: null }),
        filtersToSearch({ japanese: 'any', specialties: [], board: null }),
        filtersToSearch({ japanese: 'any', specialties: null, board: null }),
    ]

    expect(searches).toEqual(['japanese=conversational&specialty=backend,ml', 'japanese=none', 'specialty=', ''])
})

test('a changed filter drops sales and unknown specialties from the URL', () => {
    const filters = readFilters(new URLSearchParams('?sales=1&specialty=bogus,ml,backend'))

    expect(filtersToSearch({ ...filters, japanese: 'basic' })).toEqual('japanese=basic&specialty=backend,ml')
})

test('the postings URL asks for followed boards, My Japanese and Specialty, and leaves defaults out', () => {
    const urls = [
        postingsUrl(false, { japanese: 'any', specialties: null, board: null }),
        postingsUrl(true, { japanese: 'any', specialties: null, board: null }),
        postingsUrl(false, { japanese: 'none', specialties: [], board: null }),
        postingsUrl(true, { japanese: 'business', specialties: ['backend', 'other'], board: null }),
    ]

    expect(urls).toEqual([
        '/api/postings',
        '/api/postings?following=true',
        '/api/postings?japanese=none&specialty=',
        '/api/postings?following=true&japanese=business&specialty=backend,other',
    ])
})

test('the page goes after the filters in both URLs, and page 1 is left out', () => {
    const filters: Filters = { japanese: 'basic', specialties: ['ml'], board: null }

    expect([
        filtersToSearch(filters, 3),
        filtersToSearch(filters, 1),
        filtersToSearch({ japanese: 'any', specialties: null, board: null }, 2),
        postingsUrl(true, filters, 3),
        postingsUrl(false, { japanese: 'any', specialties: null, board: null }, 2),
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

const followed = new Set(['greenhouse:acme', 'ashby:acme'])

test('reads a followed company and round-trips it with the other filters', () => {
    const search = 'japanese=basic&specialty=backend,ml&company=greenhouse:acme&page=2'
    const filters = readFilters(new URLSearchParams(search), followed)

    expect([filters, filtersToSearch(filters, 2), filtersToSearch({ ...filters, japanese: 'native' }, 2)]).toEqual([
        { japanese: 'basic', specialties: ['backend', 'ml'], board: 'greenhouse:acme' },
        search,
        'japanese=native&specialty=backend,ml&company=greenhouse:acme&page=2',
    ])
})

test('a company the user does not follow, or one read without follows, reads as none', () => {
    const searches = ['?company=lever:acme', '?company=acme', '?company=']

    const none: Filters = { japanese: 'any', specialties: null, board: null }

    expect([
        ...searches.map((search) => readFilters(new URLSearchParams(search), followed)),
        readFilters(new URLSearchParams('?company=greenhouse:acme')),
    ]).toEqual([none, none, none, none])
})

test('the postings URL asks for the company by source and token', () => {
    const filters: Filters = { japanese: 'none', specialties: null, board: 'ashby:acme' }

    expect(postingsUrl(true, filters, 2)).toEqual('/api/postings?following=true&source=ashby&token=acme&japanese=none&page=2')
})

test('clicking a chip selects its company or clears it on page 1, and does nothing while managing', () => {
    const filters = readFilters(new URLSearchParams('?japanese=basic&company=greenhouse:acme&page=3'), followed)

    expect([
        boardClickSearch(filters, 'ashby:acme', false),
        boardClickSearch(filters, 'greenhouse:acme', false),
        boardClickSearch(filters, 'ashby:acme', true),
        boardClickSearch(filters, 'greenhouse:acme', true),
    ]).toEqual(['japanese=basic&company=ashby:acme', 'japanese=basic', null, null])
})

test('a company no longer followed drops from the URL on page 1, and a followed one stays', () => {
    const searches = [
        '?japanese=basic&company=lever:acme&page=3',
        '?company=',
        '?japanese=basic&company=greenhouse:acme&page=3',
        '?japanese=basic&page=3',
    ]

    expect(searches.map((search) => droppedBoardSearch(new URLSearchParams(search), followed))).toEqual([
        'japanese=basic',
        '',
        null,
        null,
    ])
})
