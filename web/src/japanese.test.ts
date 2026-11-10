import { expect, test } from 'vitest'
import {
    type JapaneseChoice,
    type JapaneseFacts,
    type JapaneseRequirement,
    japaneseBadge,
    japaneseRequirement,
    passesJapanese,
} from './japanese'

function facts(japanese_required: string, japanese_level: string, jlpt: string): JapaneseFacts {
    return { japanese_required, japanese_level, jlpt }
}

test('a named level wins over JLPT, and JLPT stands in when no level is named', () => {
    const cases = [
        facts('required', 'conversational', 'N1'),
        facts('required', 'native', 'N3'),
        facts('required', 'basic', 'not_stated'),
        facts('required', 'not_stated', 'N1'),
        facts('required', 'not_stated', 'N2'),
        facts('required', 'not_stated', 'N3'),
        facts('required', 'not_stated', 'N4'),
        facts('required', 'not_stated', 'N5'),
    ]

    expect(cases.map(japaneseRequirement)).toEqual([
        'conversational',
        'native',
        'basic',
        'business',
        'business',
        'conversational',
        'basic',
        'basic',
    ])
})

test('required Japanese with neither a level nor JLPT is business', () => {
    expect(japaneseRequirement(facts('required', 'not_stated', 'not_stated'))).toEqual('business')
})

test('preferred and not required are none, whatever level they name', () => {
    const cases = [
        facts('preferred', 'business', 'N2'),
        facts('preferred', 'not_stated', 'not_stated'),
        facts('not_required', 'not_stated', 'not_stated'),
        facts('not_required', 'conversational', 'N3'),
    ]

    expect(cases.map(japaneseRequirement)).toEqual(['none', 'none', 'none', 'none'])
})

test('not stated is not stated, unless a level or JLPT is named anyway', () => {
    const cases = [
        facts('not_stated', 'not_stated', 'not_stated'),
        facts('not_stated', 'business', 'not_stated'),
        facts('not_stated', 'not_stated', 'N3'),
    ]

    expect(cases.map(japaneseRequirement)).toEqual(['not_stated', 'business', 'conversational'])
})

test('the badge names the level, and tells preferred, not required and not stated apart', () => {
    const cases = [
        facts('required', 'basic', 'not_stated'),
        facts('required', 'not_stated', 'N3'),
        facts('required', 'not_stated', 'not_stated'),
        facts('required', 'native', 'not_stated'),
        facts('preferred', 'business', 'not_stated'),
        facts('not_required', 'not_stated', 'not_stated'),
        facts('not_stated', 'not_stated', 'not_stated'),
    ]

    expect(cases.map(japaneseBadge)).toEqual([
        'Basic Japanese',
        'Conversational Japanese',
        'Business Japanese',
        'Native Japanese',
        'Japanese preferred',
        'No Japanese',
        'Japanese not stated',
    ])
})

test('a choice passes requirements up to its own level, and none and not stated always pass', () => {
    const requirements: JapaneseRequirement[] = ['none', 'not_stated', 'basic', 'conversational', 'business', 'native']
    const choices: JapaneseChoice[] = ['any', 'none', 'basic', 'conversational', 'business', 'native']

    const passing = Object.fromEntries(
        choices.map((choice) => [choice, requirements.filter((requirement) => passesJapanese(requirement, choice))]),
    )

    expect(passing).toEqual({
        any: ['none', 'not_stated', 'basic', 'conversational', 'business', 'native'],
        none: ['none', 'not_stated'],
        basic: ['none', 'not_stated', 'basic'],
        conversational: ['none', 'not_stated', 'basic', 'conversational'],
        business: ['none', 'not_stated', 'basic', 'conversational', 'business'],
        native: ['none', 'not_stated', 'basic', 'conversational', 'business', 'native'],
    })
})
