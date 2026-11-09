import { Link } from 'react-router'
import NewBadge from './NewBadge'
import Title from './Title'

export type Tracked = {
    id: number
    status: string
    note: string
    posting: { id: number; title: string; url: string; location: string; first_seen_at: string; listed: boolean }
}

export default function TrackedPostings({ tracked }: { tracked: Tracked[] }) {
    return (
        <main>
            <Title>Tracked · kansei</Title>
            <h1>Tracked postings</h1>
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
                            {row.status} · {row.posting.location}
                            {!row.posting.listed && ' · No longer listed'}
                        </span>
                    </li>
                ))}
            </ul>
        </main>
    )
}
