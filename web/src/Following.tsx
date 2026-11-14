import { useState } from 'react'
import AddCompany from './AddCompany'
import { type Board, type FollowControls } from './boards'
import CompanyLogo from './CompanyLogo'
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
                <ul className="follow-chips">
                    {followChips(follows).map(({ key, board, source }) => (
                        <li key={key} className="follow-chip">
                            <CompanyLogo company={board.company} logoUrl={board.logo_url} />
                            <span className="follow-chip-name">{board.company}</span>
                            {source && <span className="follow-chip-source">{source}</span>}
                            {managing && (
                                <button
                                    className="follow-chip-unfollow"
                                    aria-label={source ? `Unfollow ${board.company} on ${source}` : `Unfollow ${board.company}`}
                                    disabled={following.pending.has(key)}
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
            {follows.length > 0 && (
                <Postings followingOnly tracking={tracking} following={following} />
            )}
        </main>
    )
}
