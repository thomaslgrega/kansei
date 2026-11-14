import { expect, test } from 'vitest'
import type { Board } from './boards'
import { followChips } from './followChips'

function board(source: string, token: string, company: string): Board {
    return { source, token, company, logo_url: null }
}

test('only boards that share a company name with another followed board name their source', () => {
    const greenhouseMercari = board('greenhouse', 'mercari', 'Mercari')
    const hrmosMercari = board('hrmos', 'mercari', 'mercari')
    const mujin = { ...board('lever', 'mujin', 'Mujin'), logo_url: 'https://example.com/mujin.png' }
    const ashbyStripe = board('ashby', 'stripe', 'Stripe')
    const greenhouseStripe = board('greenhouse', 'stripe', 'Stripe')
    const greenhouseStripeJp = board('greenhouse', 'stripe-jp', 'Stripe')

    const chips = followChips([greenhouseMercari, hrmosMercari, mujin, ashbyStripe, greenhouseStripe, greenhouseStripeJp], {}, false)

    expect(chips).toEqual([
        { board: greenhouseMercari, sourceLabel: 'greenhouse', newLabel: null },
        { board: hrmosMercari, sourceLabel: 'hrmos', newLabel: null },
        { board: mujin, sourceLabel: null, newLabel: null },
        { board: ashbyStripe, sourceLabel: 'ashby', newLabel: null },
        { board: greenhouseStripe, sourceLabel: 'greenhouse', newLabel: null },
        { board: greenhouseStripeJp, sourceLabel: 'greenhouse', newLabel: null },
    ])
})

test('a chip says how many new candidates its board has, only when there are some', () => {
    const mercari = board('greenhouse', 'mercari', 'Mercari')
    const mujin = board('lever', 'mujin', 'Mujin')
    const stripe = board('ashby', 'stripe', 'Stripe')
    const counts = { 'greenhouse:mercari': 3, 'lever:mujin': 0, 'hrmos:other': 2 }

    const chips = followChips([mercari, mujin, stripe], counts, false)

    expect(chips).toEqual([
        { board: mercari, sourceLabel: null, newLabel: '3 new' },
        { board: mujin, sourceLabel: null, newLabel: null },
        { board: stripe, sourceLabel: null, newLabel: null },
    ])
})

test('no chip counts new candidates while managing follows', () => {
    const mercari = board('greenhouse', 'mercari', 'Mercari')

    const chips = followChips([mercari], { 'greenhouse:mercari': 3 }, true)

    expect(chips).toEqual([{ board: mercari, sourceLabel: null, newLabel: null }])
})
