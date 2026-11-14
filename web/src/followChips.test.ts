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

    const chips = followChips([greenhouseMercari, hrmosMercari, mujin, ashbyStripe, greenhouseStripe, greenhouseStripeJp])

    expect(chips).toEqual([
        { board: greenhouseMercari, sourceLabel: 'greenhouse' },
        { board: hrmosMercari, sourceLabel: 'hrmos' },
        { board: mujin, sourceLabel: null },
        { board: ashbyStripe, sourceLabel: 'ashby' },
        { board: greenhouseStripe, sourceLabel: 'greenhouse' },
        { board: greenhouseStripeJp, sourceLabel: 'greenhouse' },
    ])
})
