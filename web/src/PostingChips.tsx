import type { Chip } from './chips'

export default function PostingChips({ chips }: { chips: Chip[] }) {
    return (
        <ul className="chips">
            {chips.map((chip, index) => (
                <li key={index} className={chipClass(chip)}>
                    {chip.label}
                </li>
            ))}
        </ul>
    )
}

function chipClass(chip: Chip): string {
    if (chip.kind === 'japanese') return `chip japanese japanese-${chip.requirement}`
    if (chip.kind === 'skill' && chip.marked) return 'chip skill marked'
    return `chip ${chip.kind}`
}
