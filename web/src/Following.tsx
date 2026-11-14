import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router'
import AddCompany from './AddCompany'
import { type Board, boardKey, type FollowControls } from './boards'
import CompanyLogo from './CompanyLogo'
import { boardClickSearch, droppedBoardSearch, filtersToSearch, readFilters } from './filters'
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

    return (
        <main>
            <Title>Following · kansei</Title>
            <div className="following-heading">
                <h1>Following</h1>
                {follows.length > 0 && (
                    <>
                        <span className="muted">
                            {follows.length} {follows.length === 1 ? 'company' : 'companies'}
                        </span>
                        <button className="link-button following-manage" onClick={() => setManaging(!managing)}>
                            {managing ? 'Done' : 'Manage'}
                        </button>
                    </>
                )}
            </div>
            {follows.length === 0 ? (
                <p>
                    You don't follow any companies yet. Find one under <a href="#add-company">Add a company</a>, and
                    its postings will show here.
                </p>
            ) : (
                <ul className={managing ? 'follow-chips managing' : 'follow-chips'}>
                    {followChips(follows).map(({ board, sourceLabel }) => (
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
            )}
            {managing && <p className="muted following-hint">Click × to unfollow.</p>}
            <h2 id="add-company">Add a company</h2>
            <AddCompany followed={following.keys} onFollowsChanged={onFollowsChanged} />
            {selected && (
                <p className="following-selected">
                    Showing only <strong>{selected.company}</strong> ·{' '}
                    <button className="link-button" onClick={() => go(filtersToSearch({ ...filters, board: null }))}>
                        Show all
                    </button>
                </p>
            )}
            {follows.length > 0 && (
                <Postings followingOnly tracking={tracking} following={following} />
            )}
        </main>
    )
}
