import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router'
import AddCompany from './AddCompany'
import { type Board, boardKey, type FollowControls, followsKey } from './boards'
import CompanyLogo from './CompanyLogo'
import { boardClickSearch, droppedBoardSearch, filtersToSearch, newCountsUrl, readFilters } from './filters'
import { followChips } from './followChips'
import Postings from './Postings'
import Title from './Title'
import type { TrackControls } from './tracked'

type Props = {
    follows: Board[]
    following: FollowControls
    onFollowsChanged: () => Promise<void>
    tracking: TrackControls
}

export default function Following({ follows, following, onFollowsChanged, tracking }: Props) {
    const [managing, setManaging] = useState(false)
    const [panelOpen, setPanelOpen] = useState(false)
    const [notice, setNotice] = useState('')
    if (managing && follows.length === 0) setManaging(false)
    const [params] = useSearchParams()
    const navigate = useNavigate()
    const filters = readFilters(params, following.keys)
    const selected = follows.find((board) => boardKey(board) === filters.board)

    const dropped = droppedBoardSearch(params, following.keys)
    useEffect(() => {
        if (dropped !== null) navigate(`?${dropped}`, { replace: true })
    }, [dropped, navigate])

    function go(search: string | null) {
        if (search !== null) navigate(`?${search}`, { replace: true })
    }

    const newCounts = useNewCounts(newCountsUrl(filters), followsKey(following.keys))

    function showFollowed(message: string) {
        setPanelOpen(false)
        setNotice(message)
    }

    if (follows.length === 0) {
        return (
            <main>
                <Title>Following · kansei</Title>
                <h1>Following</h1>
                <p>Follow a company and its Japan engineering postings will show here.</p>
                <AddCompany followed={following.keys} onFollowsChanged={onFollowsChanged} onFollowed={showFollowed} />
            </main>
        )
    }

    return (
        <main>
            <Title>Following · kansei</Title>
            <div className="following-heading">
                <h1>Following</h1>
                <span className="muted">
                    {follows.length} {follows.length === 1 ? 'company' : 'companies'}
                </span>
                <div className="following-actions">
                    <button className="link-button" onClick={() => setManaging(!managing)}>
                        {managing ? 'Done' : 'Manage'}
                    </button>
                    <button
                        className={panelOpen ? 'add-button open' : 'add-button'}
                        aria-expanded={panelOpen}
                        aria-controls="add-company"
                        onClick={() => {
                            setNotice('')
                            setPanelOpen(!panelOpen)
                        }}
                    >
                        {panelOpen ? 'Close' : '+ Add company'}
                    </button>
                </div>
            </div>
            {panelOpen && (
                <section id="add-company" className="add-panel" aria-label="Add a company">
                    <AddCompany followed={following.keys} onFollowsChanged={onFollowsChanged} onFollowed={showFollowed} autoFocus />
                </section>
            )}
            {notice && <p className="add-notice" role="status">{notice}</p>}
            <ul className={managing ? 'follow-chips managing' : 'follow-chips'}>
                {followChips(follows, newCounts, managing).map(({ board, sourceLabel, newLabel }) => (
                    <li key={boardKey(board)} className="follow-chip-item">
                        <button
                            className="follow-chip"
                            aria-pressed={boardKey(board) === filters.board}
                            aria-disabled={managing}
                            onClick={() => go(boardClickSearch(filters, boardKey(board), managing))}
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
                                disabled={following.pending.has(boardKey(board))}
                                onClick={() => following.unfollow(board.source, board.token)}
                            >
                                ×
                            </button>
                        )}
                    </li>
                ))}
            </ul>
            {managing && <p className="muted following-hint">Click × to unfollow.</p>}
            {selected && (
                <p className="following-selected">
                    Showing only <strong>{selected.company}</strong> ·{' '}
                    <button className="link-button" onClick={() => go(filtersToSearch({ ...filters, board: null }))}>
                        Show all
                    </button>
                </p>
            )}
            <Postings followingOnly tracking={tracking} following={following} />
        </main>
    )
}

// Refetches when follows change too, so a newly followed board gets its count.
function useNewCounts(url: string, followsSignature: string): Record<string, number> {
    const [counts, setCounts] = useState<Record<string, number>>({})
    useEffect(() => {
        let current = true
        fetch(url)
            .then((response) => {
                if (!response.ok) throw new Error(`GET ${url}: ${response.status}`)
                return response.json()
            })
            .then((body: Record<string, number>) => current && setCounts(body))
            .catch(() => current && setCounts({}))
        return () => {
            current = false
        }
    }, [url, followsSignature])
    return counts
}
