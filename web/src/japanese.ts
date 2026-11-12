export type JapaneseRequired = 'required' | 'preferred' | 'not_required' | 'not_stated'

const LEVELS = ['basic', 'conversational', 'business', 'native'] as const

type Level = (typeof LEVELS)[number]

export type JapaneseRequirement = Level | 'none' | 'not_stated'

export type JapaneseChoice = 'any' | 'none' | Level

export const JAPANESE_CHOICES: readonly JapaneseChoice[] = ['any', 'none', ...LEVELS]

export function readJapaneseChoice(value: string | null): JapaneseChoice {
    return JAPANESE_CHOICES.find((choice) => choice === value) ?? 'any'
}

export function capitalize(value: string): string {
    return value.charAt(0).toUpperCase() + value.slice(1)
}

export function japaneseBadge(requirement: JapaneseRequirement, required: JapaneseRequired): string {
    if (requirement === 'not_stated') return 'Japanese not stated'
    if (requirement !== 'none') return `${capitalize(requirement)} Japanese`
    return required === 'preferred' ? 'Japanese preferred' : 'No Japanese'
}
