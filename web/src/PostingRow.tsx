import { type ReactNode, useState } from 'react'
import { type ChipFacts, postingChips } from './chips'
import { companyTile, shownLogo } from './companyTile'
import { firstSeenAgo } from './firstSeen'
import NewBadge from './NewBadge'

export type Posting = {
    id: number
    url: string
    source: string
    token: string
    company: string
    logo_url: string | null
    has_board: boolean
    title: string
    location: string
    first_seen_at: string
    last_seen_at: string
}

export type Facts = ChipFacts & { role_summary: string }

type Props = {
    posting: Posting
    facts: Facts
    actions?: ReactNode
    companyAction?: ReactNode
}

export default function PostingRow({ posting, facts, actions, companyAction }: Props) {
    const [now] = useState(Date.now)
    const [failedLogo, setFailedLogo] = useState<string | null>(null)
    const logo = shownLogo(posting.logo_url, failedLogo)
    const tile = companyTile(posting.company)

    return (
        <li className="posting">
            {logo ? (
                <img
                    className="tile tile-logo"
                    src={logo}
                    alt=""
                    loading="lazy"
                    referrerPolicy="no-referrer"
                    onError={() => setFailedLogo(logo)}
                />
            ) : (
                <span className="tile" style={{ background: tile.color }} aria-hidden="true">
                    {tile.letter}
                </span>
            )}
            <div className="posting-body">
                <h3 className="posting-title">
                    <NewBadge firstSeenAt={posting.first_seen_at} />
                    <a href={posting.url} target="_blank">
                        {posting.title}
                    </a>
                </h3>
                <p className="muted">
                    <span className="posting-company">{posting.company}</span>
                    {companyAction} · {posting.location} · first seen{' '}
                    <time dateTime={posting.first_seen_at} title={new Date(posting.first_seen_at).toLocaleDateString('en-CA')}>
                        {firstSeenAgo(posting.first_seen_at, now)}
                    </time>
                </p>
                <p className="muted">{facts.role_summary}</p>
                <ul className="chips">
                    {postingChips(facts).map((chip, index) => (
                        <li key={index} className={chip.kind === 'japanese' ? `chip japanese japanese-${chip.requirement}` : `chip ${chip.kind}`}>
                            {chip.label}
                        </li>
                    ))}
                </ul>
            </div>
            {actions && <div className="posting-actions">{actions}</div>}
        </li>
    )
}
