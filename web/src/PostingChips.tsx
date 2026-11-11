import type { Chip } from './chips'

export default function PostingChips({ chips }: { chips: Chip[] }) {
    return (
        <ul className="chips">
            {chips.map((chip, index) => (
                <li key={index} className={chip.kind === 'japanese' ? `chip japanese japanese-${chip.requirement}` : `chip ${chip.kind}`}>
                    {chip.label}
                </li>
            ))}
        </ul>
    )
}
