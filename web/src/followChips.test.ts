import { expect, test } from 'vitest'
import type { Board } from './boards'
import { clampChips, type FollowChip, followChips, twoRowFit } from './followChips'

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

function chipsFor(...tokens: string[]): FollowChip[] {
    return tokens.map((token) => ({ board: board('greenhouse', token, token), sourceLabel: null, newLabel: null }))
}

test('chips past the clamp are hidden and counted', () => {
    const chips = chipsFor('a', 'b', 'c', 'd', 'e')

    expect(clampChips(chips, 3, null)).toEqual({ shown: chips.slice(0, 3), hidden: 2 })
})

test('nothing is hidden when every chip fits', () => {
    const chips = chipsFor('a', 'b', 'c')

    expect(clampChips(chips, 5, null)).toEqual({ shown: chips, hidden: 0 })
})

test('a selected chip already in view stays where it is', () => {
    const chips = chipsFor('a', 'b', 'c', 'd', 'e')

    expect(clampChips(chips, 3, 'greenhouse:b')).toEqual({ shown: chips.slice(0, 3), hidden: 2 })
})

test('a selected chip past the clamp takes the last visible place, and the count covers the others', () => {
    const [a, b, c, d, e] = chipsFor('a', 'b', 'c', 'd', 'e')

    expect(clampChips([a, b, c, d, e], 3, 'greenhouse:e')).toEqual({ shown: [a, b, e], hidden: 2 })
})

test('chips that fit in two rows are all kept', () => {
    expect(twoRowFit([0, 0, 0, 40, 40, 40], 5)).toEqual(5)
})

test('a third row drops the chips on it', () => {
    expect(twoRowFit([0, 0, 40, 40, 80, 80, 80], 6)).toEqual(4)
})

test('a "+N more" chip alone on the third row drops one chip', () => {
    expect(twoRowFit([0, 0, 0, 40, 40, 40, 80], 6)).toEqual(5)
})

test('no chips are kept when even the second row overflows past the first chip', () => {
    expect(twoRowFit([0, 40, 80], 1)).toEqual(0)
})
