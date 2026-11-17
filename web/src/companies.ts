import { boardKey } from './boards'
import { type Filters, filtersToSearch } from './filters'

export type MatchedBoard = { source: string; token: string; company: string; exact: boolean; removed: boolean }

export type Ending = { kind: 'add' } | { kind: 'removed'; company: string }

export type CompaniesLine =
    | { kind: 'one'; board: MatchedBoard }
    | { kind: 'matching'; boards: MatchedBoard[]; ending: Ending | null }
    | { kind: 'none'; ending: Ending }

// A removed board can't be added again, so as the exact match it takes the Add link's place.
export function companiesLine(companies: MatchedBoard[]): CompaniesLine {
    const boards = companies.filter((board) => !board.removed)
    const exact = boards.some((board) => board.exact)
    if (exact && boards.length === 1) return { kind: 'one', board: boards[0] }
    const removed = companies.find((board) => board.removed && board.exact)
    const ending: Ending = removed ? { kind: 'removed', company: removed.company } : { kind: 'add' }
    if (boards.length === 0) return { kind: 'none', ending }
    return { kind: 'matching', boards, ending: exact ? null : ending }
}

export function boardHref(filters: Filters, board: { source: string; token: string }): string {
    return `/?${filtersToSearch({ ...filters, query: '', board: boardKey(board) })}`
}

export function addCompanyHref(query: string): string {
    return `/following?${new URLSearchParams({ add: query })}`
}
