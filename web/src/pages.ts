export const PAGE_SIZE = 50

export type PageNumber = number | '…'

export function readPage(params: URLSearchParams): number {
    const page = Number(params.get('page'))
    return Number.isInteger(page) && page >= 1 ? page : 1
}

export function lastPage(total: number): number {
    return Math.max(1, Math.ceil(total / PAGE_SIZE))
}

function pagesFrom(first: number, last: number): number[] {
    return Array.from({ length: last - first + 1 }, (_, index) => first + index)
}

// Always 7 slots once there are more than 7 pages, so the buttons don't shift under the pointer.
export function pageNumbers(current: number, last: number): PageNumber[] {
    if (last <= 7) return pagesFrom(1, last)
    if (current <= 4) return [...pagesFrom(1, 5), '…', last]
    if (current >= last - 3) return [1, '…', ...pagesFrom(last - 4, last)]
    return [1, '…', current - 1, current, current + 1, '…', last]
}

export function pageRange(page: number, total: number): string {
    const first = (page - 1) * PAGE_SIZE + 1
    const last = Math.min(page * PAGE_SIZE, total)
    return first === last ? `${first} of ${total}` : `${first}–${last} of ${total}`
}
