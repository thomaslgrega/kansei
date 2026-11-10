export type JapaneseFacts = {
    japanese_required: 'required' | 'preferred' | 'not_required' | 'not_stated'
    japanese_level: string
    jlpt: string
}

const LEVELS = ['basic', 'conversational', 'business', 'native'] as const

type Level = (typeof LEVELS)[number]

export type JapaneseRequirement = Level | 'none' | 'not_stated'

export type JapaneseChoice = 'any' | 'none' | Level

export const JAPANESE_CHOICES: readonly JapaneseChoice[] = ['any', 'none', ...LEVELS]

export function readJapaneseChoice(value: string | null): JapaneseChoice {
    return JAPANESE_CHOICES.find((choice) => choice === value) ?? 'any'
}

const JLPT_LEVELS = new Map<string, Level>([
    ['N1', 'business'],
    ['N2', 'business'],
    ['N3', 'conversational'],
    ['N4', 'basic'],
    ['N5', 'basic'],
])

function isLevel(value: string): value is Level {
    return (LEVELS as readonly string[]).includes(value)
}

export function japaneseRequirement(facts: JapaneseFacts): JapaneseRequirement {
    if (facts.japanese_required === 'not_stated') return 'not_stated'
    if (facts.japanese_required !== 'required') return 'none'
    if (isLevel(facts.japanese_level)) return facts.japanese_level
    return JLPT_LEVELS.get(facts.jlpt) ?? 'business'
}

export function capitalize(value: string): string {
    return value.charAt(0).toUpperCase() + value.slice(1)
}

export function japaneseBadge(facts: JapaneseFacts): string {
    if (facts.japanese_required === 'preferred') return 'Japanese preferred'
    if (facts.japanese_required === 'not_required') return 'No Japanese'
    const requirement = japaneseRequirement(facts)
    return requirement === 'not_stated' ? 'Japanese not stated' : `${capitalize(requirement)} Japanese`
}

export function passesJapanese(requirement: JapaneseRequirement, choice: JapaneseChoice): boolean {
    if (choice === 'any' || requirement === 'none' || requirement === 'not_stated') return true
    return choice !== 'none' && LEVELS.indexOf(requirement) <= LEVELS.indexOf(choice)
}
