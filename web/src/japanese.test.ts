import { expect, test } from 'vitest'
import { type JapaneseRequired, type JapaneseRequirement, japaneseBadge } from './japanese'

test('the badge names the level, and tells preferred, not required and not stated apart', () => {
    const cases: [JapaneseRequirement, JapaneseRequired][] = [
        ['basic', 'required'],
        ['conversational', 'required'],
        ['business', 'required'],
        ['native', 'required'],
        ['none', 'preferred'],
        ['none', 'not_required'],
        ['not_stated', 'not_stated'],
    ]

    expect(cases.map(([requirement, required]) => japaneseBadge(requirement, required))).toEqual([
        'Basic Japanese',
        'Conversational Japanese',
        'Business Japanese',
        'Native Japanese',
        'Japanese preferred',
        'No Japanese',
        'Japanese not stated',
    ])
})
