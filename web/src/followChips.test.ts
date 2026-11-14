import { expect, test } from 'vitest'
import type { Board } from './boards'
import { followChips } from './followChips'

function board(source: string, token: string, company: string): Board {
    return { source, token, company, logo_url: null }
}

test('only boards that share a company name with another followed board name their source', () => {
    const boards = [
        board('greenhouse', 'mercari', 'Mercari'),
        board('hrmos', 'mercari', 'mercari'),
        board('lever', 'mujin', 'Mujin'),
        board('ashby', 'stripe', 'Stripe'),
        board('greenhouse', 'stripe', 'Stripe'),
        board('greenhouse', 'stripe-jp', 'Stripe'),
    ]

    expect(followChips(boards).map((chip) => [chip.key, chip.source])).toEqual([
        ['greenhouse:mercari', 'greenhouse'],
        ['hrmos:mercari', 'hrmos'],
        ['lever:mujin', null],
        ['ashby:stripe', 'ashby'],
        ['greenhouse:stripe', 'greenhouse'],
        ['greenhouse:stripe-jp', 'greenhouse'],
    ])
})
