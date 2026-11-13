import { expect, test } from 'vitest'
import { lastPage, pageNumbers, pageRange, readPage } from './pages'

test('reads the page from the query string, and anything but a positive whole number as page 1', () => {
    const searches = ['?page=3', '?page=1', '?page=0', '?page=-2', '?page=two', '?page=2.5', '?page=', '']

    expect(searches.map((search) => readPage(new URLSearchParams(search)))).toEqual([3, 1, 1, 1, 1, 1, 1, 1])
})

test('the last page holds what is left after full pages of 50, and nothing is one page', () => {
    expect([0, 1, 50, 51, 100, 312].map(lastPage)).toEqual([1, 1, 1, 2, 2, 7])
})

test('page numbers list every page up to 7, and otherwise keep 7 slots with ellipses', () => {
    const cases: [number, number][] = [[1, 2], [4, 7], [1, 8], [4, 8], [5, 8], [5, 10], [6, 10], [7, 10], [10, 10]]

    expect(cases.map(([current, last]) => pageNumbers(current, last))).toEqual([
        [1, 2],
        [1, 2, 3, 4, 5, 6, 7],
        [1, 2, 3, 4, 5, '…', 8],
        [1, 2, 3, 4, 5, '…', 8],
        [1, '…', 4, 5, 6, 7, 8],
        [1, '…', 4, 5, 6, '…', 10],
        [1, '…', 5, 6, 7, '…', 10],
        [1, '…', 6, 7, 8, 9, 10],
        [1, '…', 6, 7, 8, 9, 10],
    ])
})

test('the range names the rows shown and the total', () => {
    expect([pageRange(1, 312), pageRange(2, 312), pageRange(7, 312), pageRange(2, 51)]).toEqual([
        '1–50 of 312',
        '51–100 of 312',
        '301–312 of 312',
        '51 of 51',
    ])
})
