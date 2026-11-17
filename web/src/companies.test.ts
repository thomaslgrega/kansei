import { expect, test } from 'vitest'
import { addCompanyHref, companiesLine, companyHref, emptyMessage, type MatchedBoard } from './companies'
import type { Filters } from './filters'

function board(company: string, exact: boolean, removed = false): MatchedBoard {
    return { source: 'greenhouse', token: company.toLowerCase().replaceAll(' ', '-'), company, exact, removed }
}

const stripe = board('Stripe', true)
const stripes = board('Stripes Inc', false)
const removedStripe = board('Stripe', true, true)
const removedStripes = board('Stripes Inc', false, true)

test('picks the companies line for each case', () => {
    const answers = [
        [stripe],
        [stripe, stripes],
        [],
        [stripes],
        [removedStripe],
        [removedStripe, stripes],
        [removedStripes],
        [stripe, removedStripes],
        [stripe, { ...removedStripe, source: 'lever' }],
    ]

    expect(answers.map(companiesLine)).toEqual([
        { kind: 'one', board: stripe },
        { kind: 'matching', boards: [stripe, stripes], ending: null },
        { kind: 'none', ending: { kind: 'add' } },
        { kind: 'matching', boards: [stripes], ending: { kind: 'add' } },
        { kind: 'none', ending: { kind: 'removed', company: 'Stripe' } },
        { kind: 'matching', boards: [stripes], ending: { kind: 'removed', company: 'Stripe' } },
        { kind: 'none', ending: { kind: 'add' } },
        { kind: 'one', board: stripe },
        { kind: 'one', board: stripe },
    ])
})

const filters: Filters = { japanese: 'business', specialties: ['backend', 'ml'], board: null, query: 'stripe backend' }

test('a company link opens its company view, keeping the filters and dropping the search', () => {
    expect([companyHref(filters, stripe), companyHref({ ...filters, japanese: 'any', specialties: null }, removedStripes)]).toEqual([
        '/?japanese=business&specialty=backend,ml&company=greenhouse:stripe',
        '/?company=greenhouse:stripes-inc',
    ])
})

test('the add link opens Following with the search to add', () => {
    expect([addCompanyHref('stripe'), addCompanyHref('woven by toyota'), addCompanyHref('a&b')]).toEqual([
        '/following?add=stripe',
        '/following?add=woven+by+toyota',
        '/following?add=a%26b',
    ])
})

test('picks the empty message from the answer', () => {
    const cases = [
        { filters, served: { total: 3, filtered_out: false }, narrowed: false },
        { filters, served: { total: 0, filtered_out: true }, narrowed: false },
        { filters: { ...filters, query: '', board: 'greenhouse:stripe' }, served: { total: 0, filtered_out: true }, narrowed: true },
        { filters, served: { total: 0, filtered_out: false }, narrowed: false },
        { filters, served: { total: 0, filtered_out: false }, narrowed: true },
        { filters: { ...filters, query: '' }, served: { total: 0, filtered_out: false }, narrowed: true },
        { filters: { ...filters, query: '' }, served: { total: 0, filtered_out: false }, narrowed: false },
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
