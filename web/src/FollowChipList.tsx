import { useLayoutEffect, useRef, useState } from 'react'
import { flushSync } from 'react-dom'
import { type Board, boardKey } from './boards'
import CompanyLogo from './CompanyLogo'
import { clampChips, type FollowChip, twoRowFit } from './followChips'

type Props = {
    chips: FollowChip[]
    selected: string | null
    managing: boolean
    pending: Set<string>
    onClick: (key: string) => void
    onUnfollow: (board: Board) => void
}

export default function FollowChipList({ chips, selected, managing, pending, onClick, onUnfollow }: Props) {
    const [expanded, setExpanded] = useState(false)
    const [limit, setLimit] = useState(Infinity)
    const list = useRef<HTMLUListElement>(null)

    // Anything that changes a chip's width shows every chip again, and the layout effect drops them until two rows hold.
    const layoutKey = [managing, selected, ...chips.map((chip) => `${boardKey(chip.board)} ${chip.sourceLabel} ${chip.newLabel}`)].join('|')
    const [measuredFor, setMeasuredFor] = useState(layoutKey)
    if (measuredFor !== layoutKey) {
        setMeasuredFor(layoutKey)
        setLimit(Infinity)
    }

    useLayoutEffect(() => {
        const element = list.current
        if (!element) return
        let width = element.clientWidth
        const observer = new ResizeObserver(() => {
            if (element.clientWidth === width) return
            width = element.clientWidth
            flushSync(() => setLimit(Infinity))
        })
        observer.observe(element)
        return () => observer.disconnect()
    }, [])

    const { shown, hidden } = expanded ? { shown: chips, hidden: 0 } : clampChips(chips, limit, selected)

    useLayoutEffect(() => {
        const element = list.current
        if (!element || expanded) return
        const tops = [...element.children].map((item) => (item as HTMLElement).offsetTop)
        const fit = twoRowFit(tops, shown.length)
        if (fit < shown.length) setLimit(fit)
    }, [expanded, layoutKey, limit, shown.length])

    return (
        <ul ref={list} className={managing ? 'follow-chips managing' : 'follow-chips'}>
            {shown.map(({ board, sourceLabel, newLabel }) => (
                <li key={boardKey(board)} className="follow-chip-item">
                    <button
                        className="follow-chip"
                        aria-pressed={boardKey(board) === selected}
                        aria-disabled={managing}
                        onClick={() => onClick(boardKey(board))}
                    >
                        <CompanyLogo company={board.company} logoUrl={board.logo_url} />
                        <span className="follow-chip-name">{board.company}</span>
                        {sourceLabel && <span className="follow-chip-source">{sourceLabel}</span>}
                        {newLabel && <span className="follow-chip-new">{newLabel}</span>}
                    </button>
                    {managing && (
                        <button
                            className="follow-chip-unfollow"
                            aria-label={sourceLabel ? `Unfollow ${board.company} on ${sourceLabel}` : `Unfollow ${board.company}`}
                            disabled={pending.has(boardKey(board))}
                            onClick={() => onUnfollow(board)}
                        >
                            ×
                        </button>
                    )}
                </li>
            ))}
            {(hidden > 0 || expanded) && (
                // One keyed item for both labels, so focus stays on it when it toggles.
                <li key="more" className="follow-chip-item more">
                    <button
                        className="follow-chip follow-chip-more"
                        aria-expanded={expanded}
                        onClick={() => setExpanded(!expanded)}
                    >
                        {expanded ? 'Show fewer' : `+${hidden} more`}
                    </button>
                </li>
            )}
        </ul>
    )
}
