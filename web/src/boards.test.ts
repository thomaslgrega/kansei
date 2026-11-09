import { expect, test } from 'vitest'
import { followsKey, latestOnly } from './boards'

test('a load that a newer load overtook resolves to undefined', async () => {
    const resolvers: ((value: string) => void)[] = []
    const load = latestOnly(() => new Promise<string>((resolve) => resolvers.push(resolve)))

    const older = load()
    const newer = load()
    resolvers[1]('Stripe and Mujin')
    resolvers[0]('Stripe')

    expect([await older, await newer]).toEqual([undefined, 'Stripe and Mujin'])
})

test('a load that finishes before the next one starts keeps its result', async () => {
    let calls = 0
    const load = latestOnly(async () => ++calls)

    expect([await load(), await load()]).toEqual([1, 2])
})

test('the follows key is the same for the same boards in any order and changes when one is added', () => {
    const keys = [
        followsKey(new Set(['lever:mujin', 'greenhouse:stripe'])),
        followsKey(new Set(['greenhouse:stripe', 'lever:mujin'])),
        followsKey(new Set(['greenhouse:stripe', 'lever:mujin', 'ashby:smarthr'])),
        followsKey(new Set()),
    ]

    expect(keys).toEqual([
        'greenhouse:stripe lever:mujin',
        'greenhouse:stripe lever:mujin',
        'ashby:smarthr greenhouse:stripe lever:mujin',
        '',
    ])
})
