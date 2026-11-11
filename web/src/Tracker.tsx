import { Link } from 'react-router'
import NewBadge from './NewBadge'
import Title from './Title'
import { stageLabel } from './tracked'

export type Stage = 'saved' | 'applied' | 'interviewing' | 'offer'

export type Tracked = {
    id: number
    stage: Stage
    archived: boolean
    note: string
    posting: { id: number; title: string; url: string; location: string; first_seen_at: string; listed: boolean }
}

type Props = {
    tracked: Tracked[]
}

export default function Tracker({ tracked }: Props) {
    return (
        <main>
            <Title>Tracker · kansei</Title>
            <h1>Tracker</h1>
            {tracked.length === 0 && (
                <p>
                    Nothing tracked yet. Track postings from the <Link to="/">postings list</Link>.
                </p>
            )}
            <ul>
                {tracked.map((row) => (
                    <li key={row.id}>
                        <NewBadge firstSeenAt={row.posting.first_seen_at} />
                        <a href={row.posting.url}>{row.posting.title}</a>
                        <br />
                        <span className="status">
                            {stageLabel(row)} · {row.posting.location}
                            {!row.posting.listed && ' · No longer listed'}
                        </span>
                    </li>
                ))}
            </ul>
        </main>
    )
}
