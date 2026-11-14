import { expect, test } from 'vitest'
import { readAddParam, searchWithoutAdd } from './addParam'

test('reads the company to probe from add, and nothing from an empty one', () => {
    const searches = ['?add=Stripe', '?add=%20Stripe%20Inc%20', '?add=', '?add=%20%20', '', '?company=greenhouse:acme']

    expect(searches.map((search) => readAddParam(new URLSearchParams(search)))).toEqual([
        'Stripe',
        'Stripe Inc',
        null,
        null,
        null,
        null,
    ])
})

test('removing add keeps the other params as they were', () => {
    const searches = [
        '?add=Stripe',
        '?add=Stripe&company=greenhouse:acme',
        '?specialty=backend,frontend&add=Stripe&japanese=none',
        '?company=greenhouse:acme',
    ]

    expect(searches.map((search) => searchWithoutAdd(new URLSearchParams(search)))).toEqual([
        '',
        'company=greenhouse:acme',
        'specialty=backend,frontend&japanese=none',
        'company=greenhouse:acme',
    ])
})
