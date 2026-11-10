import AddCompany from './AddCompany'
import { type Board, boardKey, type FollowControls } from './boards'
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
                            <button disabled={following.pending.has(boardKey(board))} onClick={() => following.unfollow(board.source, board.token)}>
                                Unfollow
                            </button>
                        </li>
                    ))}
                </ul>
            )}
            <h2 id="add-company">Add a company</h2>
            <AddCompany followed={following.keys} onFollowsChanged={onFollowsChanged} />
            {follows.length > 0 && (
                <Postings followingOnly tracking={tracking} following={following} />
            )}
        </main>
    )
}
