import { expect, test } from 'vitest'
import {
    boardClickSearch,
    correctedSearch,
    droppedBoardSearch,
    emptyMessage,
    type Filters,
    filtersToSearch,
    newCountsUrl,
    postingsUrl,
    querySearch,
    readFilters,
    servedQuery,
    showAllSearch,
} from './filters'

test('reads both filters from the query string and ignores sales', () => {
    const searches = ['?japanese=basic&specialty=backend,ml', '?japanese=native', '?specialty=', '?sales=1', '']

    expect(searches.map((search) => readFilters(new URLSearchParams(search)))).toEqual([
        { japanese: 'basic', specialties: ['backend', 'ml'], board: null, query: '' },
        { japanese: 'native', specialties: null, board: null, query: '' },
        { japanese: 'any', specialties: [], board: null, query: '' },
        { japanese: 'any', specialties: null, board: null, query: '' },
        { japanese: 'any', specialties: null, board: null, query: '' },
    ])
})

test('an unknown value reads as the default', () => {
    const searches = ['?japanese=fluent', '?japanese=any', '?japanese=toString']

    expect(searches.map((search) => readFilters(new URLSearchParams(search)))).toEqual([
        { japanese: 'any', specialties: null, board: null, query: '' },
        { japanese: 'any', specialties: null, board: null, query: '' },
        { japanese: 'any', specialties: null, board: null, query: '' },
    ])
})

test('writes the filters to the query string with plain commas and leaves defaults out', () => {
    const searches = [
        filtersToSearch({ japanese: 'conversational', specialties: ['backend', 'ml'], board: null, query: '' }),
        filtersToSearch({ japanese: 'none', specialties: null, board: null, query: '' }),
        filtersToSearch({ japanese: 'any', specialties: [], board: null, query: '' }),
        filtersToSearch({ japanese: 'any', specialties: null, board: null, query: '' }),
    ]

    expect(searches).toEqual(['japanese=conversational&specialty=backend,ml', 'japanese=none', 'specialty=', ''])
})

test('a changed filter drops sales and unknown specialties from the URL', () => {
    const filters = readFilters(new URLSearchParams('?sales=1&specialty=bogus,ml,backend'))

    expect(filtersToSearch({ ...filters, japanese: 'basic' })).toEqual('japanese=basic&specialty=backend,ml')
})

test('the postings URL asks for followed boards, My Japanese and Specialty, and leaves defaults out', () => {
    const urls = [
        postingsUrl(false, { japanese: 'any', specialties: null, board: null, query: '' }),
        postingsUrl(true, { japanese: 'any', specialties: null, board: null, query: '' }),
        postingsUrl(false, { japanese: 'none', specialties: [], board: null, query: '' }),
        postingsUrl(true, { japanese: 'business', specialties: ['backend', 'other'], board: null, query: '' }),
    ]

    expect(urls).toEqual([
        '/api/postings',
        '/api/postings?following=true',
        '/api/postings?japanese=none&specialty=',
        '/api/postings?following=true&japanese=business&specialty=backend,other',
    ])
})

test('the new counts URL asks for My Japanese and Specialty but not the company, and leaves defaults out', () => {
    const urls = [
        newCountsUrl({ japanese: 'any', specialties: null, board: null, query: '' }),
        newCountsUrl({ japanese: 'conversational', specialties: [], board: 'greenhouse:acme', query: '' }),
        newCountsUrl({ japanese: 'any', specialties: ['backend', 'other'], board: null, query: '' }),
    ]

    expect(urls).toEqual([
        '/api/me/follows/new',
        '/api/me/follows/new?japanese=conversational&specialty=',
        '/api/me/follows/new?specialty=backend,other',
    ])
})

test('the page goes after the filters in both URLs, and page 1 is left out', () => {
    const filters: Filters = { japanese: 'basic', specialties: ['ml'], board: null, query: '' }

    expect([
        filtersToSearch(filters, 3),
        filtersToSearch(filters, 1),
        filtersToSearch({ japanese: 'any', specialties: null, board: null, query: '' }, 2),
        postingsUrl(true, filters, 3),
        postingsUrl(false, { japanese: 'any', specialties: null, board: null, query: '' }, 2),
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
        { japanese: 'basic', specialties: ['backend', 'ml'], board: 'greenhouse:acme', query: '' },
        search,
        'japanese=native&specialty=backend,ml&company=greenhouse:acme&page=2',
    ])
})

test('on the Following page, a company the user does not follow reads as none', () => {
    const searches = ['?company=lever:acme', '?company=acme', '?company=']

    const none: Filters = { japanese: 'any', specialties: null, board: null, query: '' }

    expect(searches.map((search) => readFilters(new URLSearchParams(search), followed))).toEqual([none, none, none])
})

test('on the postings page, any company that parses reads, followed or not, and one that does not reads as none', () => {
    const searches = [
        '?company=greenhouse:acme&japanese=business',
        '?company=lever:woven-by-toyota',
        '?company=hrmos:visional',
        '?company=ashby:a:b',
        '?company=acme',
        '?company=url:careers.example.com',
        '?company=toString:acme',
        '?company=greenhouse:',
        '?company=:acme',
        '?company=',
    ]

    expect(searches.map((search) => readFilters(new URLSearchParams(search)).board)).toEqual([
        'greenhouse:acme',
        'lever:woven-by-toyota',
        'hrmos:visional',
        'ashby:a:b',
        null,
        null,
        null,
        null,
        null,
        null,
    ])
})

test('the postings URL asks for the company by source and token', () => {
    const filters: Filters = { japanese: 'none', specialties: null, board: 'ashby:acme', query: '' }

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

test('reads the search trimmed and writes it first, round-tripping commas and plus signs', () => {
    const searches = ['?japanese=basic&q=orbit+backend&page=2', '?q=++', '?q=', '?q=c%2B%2B,go']
    const filters = searches.map((search) => readFilters(new URLSearchParams(search)))

    expect([filters.map((read) => read.query), filtersToSearch(filters[0], 2), filtersToSearch(filters[3])]).toEqual([
        ['orbit backend', '', '', 'c++,go'],
        'q=orbit+backend&japanese=basic&page=2',
        'q=c%2B%2B,go',
    ])
})

test('submitting a search drops the company, so the box always searches every company', () => {
    const filters = readFilters(new URLSearchParams('?company=greenhouse:stripe&japanese=business&page=2'))

    expect([querySearch(filters, 'stripe backend'), querySearch(filters, '')]).toEqual([
        'q=stripe+backend&japanese=business',
        'japanese=business',
    ])
})

test('Show all drops the company and the page and keeps the other filters, on both pages', () => {
    const search = '?q=go&company=greenhouse:acme&japanese=business&specialty=backend,ml&page=2'

    expect([
        showAllSearch(readFilters(new URLSearchParams(search))),
        showAllSearch(readFilters(new URLSearchParams(search), followed)),
    ]).toEqual(['q=go&japanese=business&specialty=backend,ml', 'q=go&japanese=business&specialty=backend,ml'])
})

const acme = { source: 'greenhouse', token: 'acme' }

test('the postings answer corrects the page, and drops a company kansei does not have or that does not parse', () => {
    const cases: [string, { page: number; board: { source: string; token: string } | null }][] = [
        ['?company=greenhouse:acme&page=2', { page: 2, board: acme }],
        ['?japanese=basic', { page: 1, board: null }],
        ['?company=greenhouse:acme&japanese=basic&page=9', { page: 3, board: acme }],
        ['?japanese=basic&page=0', { page: 1, board: null }],
        ['?company=greenhouse:nope&japanese=basic&page=3', { page: 1, board: null }],
        ['?company=nope&specialty=ml', { page: 1, board: null }],
        ['?company=bogus:acme&page=2', { page: 2, board: null }],
    ]

    expect(cases.map(([search, served]) => {
        const params = new URLSearchParams(search)
        return correctedSearch(params, readFilters(params), served)
    })).toEqual([
        null,
        null,
        'japanese=basic&company=greenhouse:acme&page=3',
        'japanese=basic',
        'japanese=basic',
        'specialty=ml',
        'page=2',
    ])
})

test('a removed board answers with its name, so its company stays in the URL', () => {
    const params = new URLSearchParams('?company=ashby:gone&japanese=basic')

    expect(correctedSearch(params, readFilters(params), { page: 1, board: { source: 'ashby', token: 'gone' } })).toEqual(null)
})

test('on the Following page, the answer drops a company the user does not follow', () => {
    const params = new URLSearchParams('?company=lever:acme&japanese=basic')

    expect(correctedSearch(params, readFilters(params, followed), { page: 1, board: { source: 'lever', token: 'acme' } })).toEqual('japanese=basic')
})

test('submitting a search writes it on page 1, and clearing it keeps the other filters', () => {
    const filters = readFilters(new URLSearchParams('?q=old&japanese=basic&specialty=ml&page=3'))

    expect([
        querySearch(filters, '  orbit backend '),
        querySearch(filters, ''),
        querySearch(filters, '   '),
    ]).toEqual(['q=orbit+backend&japanese=basic&specialty=ml', 'japanese=basic&specialty=ml', 'japanese=basic&specialty=ml'])
})

test('the postings URL asks for the search, and the new counts URL leaves it out', () => {
    const filters: Filters = { japanese: 'none', specialties: null, board: null, query: 'エンジニア kube' }

    expect([postingsUrl(false, filters, 2), newCountsUrl(filters)]).toEqual([
        '/api/postings?q=%E3%82%A8%E3%83%B3%E3%82%B8%E3%83%8B%E3%82%A2+kube&japanese=none&page=2',
        '/api/me/follows/new?japanese=none',
    ])
})

test('reads the search an answer was fetched for', () => {
    expect(['/api/postings?q=stripe+backend&page=2', '/api/postings?japanese=basic', '/api/postings'].map(servedQuery)).toEqual([
        'stripe backend',
        '',
        '',
    ])
})

const searched: Filters = { japanese: 'business', specialties: ['backend', 'ml'], board: null, query: 'stripe backend' }

test('picks the empty message from the answer', () => {
    const cases = [
        { filters: searched, served: { total: 3, filtered_out: false }, narrowed: false },
        { filters: searched, served: { total: 0, filtered_out: true }, narrowed: false },
        { filters: { ...searched, query: '', board: 'greenhouse:stripe' }, served: { total: 0, filtered_out: true }, narrowed: true },
        { filters: searched, served: { total: 0, filtered_out: false }, narrowed: false },
        { filters: searched, served: { total: 0, filtered_out: false }, narrowed: true },
        { filters: { ...searched, query: '' }, served: { total: 0, filtered_out: false }, narrowed: true },
        { filters: { ...searched, query: '' }, served: { total: 0, filtered_out: false }, narrowed: false },
    ]

    expect(cases.map(({ filters, served, narrowed }) => emptyMessage(filters, served, narrowed))).toEqual([
        null,
        { kind: 'filtered', clear: '?q=stripe+backend' },
        { kind: 'filtered', clear: '?company=greenhouse:stripe' },
        { kind: 'query', query: 'stripe backend' },
        { kind: 'query', query: 'stripe backend' },
        { kind: 'plain' },
        null,
    ])
})
