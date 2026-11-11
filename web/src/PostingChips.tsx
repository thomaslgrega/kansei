import { type ChipFacts, postingChips } from './chips'

export default function PostingChips({ facts }: { facts: ChipFacts }) {
    return (
        <ul className="chips">
            {postingChips(facts).map((chip, index) => (
                <li key={index} className={chip.kind === 'japanese' ? `chip japanese japanese-${chip.requirement}` : `chip ${chip.kind}`}>
                    {chip.label}
                </li>
            ))}
        </ul>
    )
}
