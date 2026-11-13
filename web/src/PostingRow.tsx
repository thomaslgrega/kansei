import { type ReactNode, useState } from 'react'
import { type ChipFacts, postingChips } from './chips'
import type { JapaneseRequirement } from './japanese'
import PostingChips from './PostingChips'
import CompanyLogo from './CompanyLogo'
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
    japaneseRequirement: JapaneseRequirement
    actions?: ReactNode
    companyAction?: ReactNode
}

export default function PostingRow({ posting, facts, japaneseRequirement, actions, companyAction }: Props) {
    const [now] = useState(Date.now)

    return (
        <li className="posting">
            <CompanyLogo company={posting.company} logoUrl={posting.logo_url} />
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
                <PostingChips chips={postingChips(facts, japaneseRequirement)} />
            </div>
            {actions && <div className="posting-actions">{actions}</div>}
        </li>
    )
}
