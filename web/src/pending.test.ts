import { expect, test } from 'vitest'
import { whilePending } from './pending'

function fakeState<K>(initial: Set<K>) {
    const state = { current: initial }
    const setState = (update: (current: Set<K>) => Set<K>) => {
        state.current = update(state.current)
    }
    return { state, setState }
}

test('the key is pending while the work runs and only then, leaving other keys alone', async () => {
    const { state, setState } = fakeState(new Set([1]))
    const seen: number[][] = []

    await whilePending(setState, 2, async () => {
        seen.push([...state.current])
    })
    seen.push([...state.current])

    expect(seen).toEqual([[1, 2], [1]])
})

test('the key stops being pending when the work throws', async () => {
    const { state, setState } = fakeState(new Set<string>())

    await expect(whilePending(setState, 'greenhouse:stripe', async () => {
        throw new Error('offline')
    })).rejects.toThrow('offline')

    expect([...state.current]).toEqual([])
})
