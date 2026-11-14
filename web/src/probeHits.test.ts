import { expect, test } from 'vitest'
import { candidateCount, followedNotice, type Hit, hitAction } from './probeHits'

function hit(state: Hit['state'], token = 'acme'): Hit {
    return {
        source: 'greenhouse',
        token,
        company: 'Acme',
        titles: [],
        candidates: 2,
        state,
        following: false,
        logo_url: null,
    }
}

test('a hit offers to add, follow, says it is followed, or that it was removed', () => {
    const followed = new Set(['greenhouse:followed', 'greenhouse:gone'])

    const actions = [
        hit('not_on_kansei'),
        hit('on_kansei'),
        hit('on_kansei', 'followed'),
        hit('removed'),
        hit('removed', 'gone'),
    ].map((each) => hitAction(each, followed))

    expect(actions).toEqual(['add', 'follow', 'following', 'removed', 'removed'])
})

test('the candidate count names Japan engineering jobs, one or many', () => {
    expect([0, 1, 2].map(candidateCount)).toEqual([
        '0 Japan engineering jobs',
        '1 Japan engineering job',
        '2 Japan engineering jobs',
    ])
})

test('following a board says so, and adding one new to kansei says when its jobs appear', () => {
    const unnamed = { ...hit('on_kansei'), company: null }

    expect([hit('on_kansei'), hit('not_on_kansei'), unnamed].map(followedNotice)).toEqual([
        'Following Acme.',
        'Added Acme. Its jobs will appear after the next update.',
        'Following acme.',
    ])
})
