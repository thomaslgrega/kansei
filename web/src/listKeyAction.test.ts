import { expect, test } from 'vitest'
import { listKeyAction } from './listKeyAction'

function fromEach(key: string, count: number) {
    return Array.from({ length: count }, (_, highlighted) => listKeyAction(highlighted, key, count))
}

test('the arrows move one option and stop at both ends of the list', () => {
    expect([fromEach('ArrowDown', 3), fromEach('ArrowUp', 3)]).toEqual([
        [1, 2, 2],
        [0, 0, 1],
    ])
})

test('Home jumps to the first option and End to the last, from anywhere', () => {
    expect([fromEach('Home', 3), fromEach('End', 3)]).toEqual([
        [0, 0, 0],
        [2, 2, 2],
    ])
})

test('Enter and Space pick the highlighted option', () => {
    expect([fromEach('Enter', 3), fromEach(' ', 3)]).toEqual([
        ['pick', 'pick', 'pick'],
        ['pick', 'pick', 'pick'],
    ])
})

test('Escape and Tab close the list', () => {
    expect([fromEach('Escape', 3), fromEach('Tab', 3)]).toEqual([
        ['close', 'close', 'close'],
        ['close', 'close', 'close'],
    ])
})

test('in a one-option list every move stays on that option', () => {
    expect(['ArrowDown', 'ArrowUp', 'Home', 'End'].map((key) => listKeyAction(0, key, 1))).toEqual([0, 0, 0, 0])
})

test('other keys are left alone', () => {
    expect([fromEach('a', 3), fromEach('ArrowLeft', 3), fromEach('PageDown', 3)]).toEqual([
        [null, null, null],
        [null, null, null],
        [null, null, null],
    ])
})
