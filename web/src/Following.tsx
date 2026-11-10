import AddCompany from './AddCompany'
import { type Board, boardKey } from './boards'
import Postings from './Postings'
import Title from './Title'

type Props = {
    follows: Board[]
    pendingFollows: Set<string>
    onFollow: (source: string, token: string) => void
    onUnfollow: (source: string, token: string) => void
    onFollowsChanged: () => Promise<void>
    trackedIds: Set<number>
    pendingTracks: Set<number>
    onTrack: (postingId: number) => void
    onUntrack: (postingId: number) => void
}

export default function Following({ follows, pendingFollows, onFollow, onUnfollow, onFollowsChanged, trackedIds, pendingTracks, onTrack, onUntrack }: Props) {
    const followed = new Set(follows.map(boardKey))

    return (
        <main>
            <Title>Following · kansei</Title>
            <h1>Following</h1>
            {follows.length === 0 ? (
                <p>
                    You don't follow any companies yet. Find one under <a href="#add-company">Add a company</a>, and
                    its postings will show here.
                </p>
            ) : (
                <ul>
                    {follows.map((board) => (
                        <li key={boardKey(board)}>
                            {board.company}{' '}
                            <button disabled={pendingFollows.has(boardKey(board))} onClick={() => onUnfollow(board.source, board.token)}>
                                Unfollow
                            </button>
                        </li>
                    ))}
                </ul>
            )}
            <h2 id="add-company">Add a company</h2>
            <AddCompany followed={followed} onFollowsChanged={onFollowsChanged} />
            {follows.length > 0 && (
                <Postings
                    followingOnly
                    trackedIds={trackedIds}
                    pendingTracks={pendingTracks}
                    onTrack={onTrack}
                    onUntrack={onUntrack}
                    followed={followed}
                    pendingFollows={pendingFollows}
                    onFollow={onFollow}
                    onUnfollow={onUnfollow}
                />
            )}
        </main>
    )
}
