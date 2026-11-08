import { expect, test } from 'vitest'
import { latestOnly } from './boards'

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
