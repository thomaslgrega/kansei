import { expect, test } from 'vitest'
import { allPostingChips, type ChipFacts, postingChips } from './chips'
import type { JapaneseRequirement } from './japanese'

const SKILLS = ['Go', 'Kubernetes', 'PostgreSQL', 'gRPC', 'Terraform', 'AWS', 'Kafka']

function facts(change: Partial<ChipFacts>): ChipFacts {
    return {
        japanese_required: 'not_stated',
        remote_policy: 'not_stated',
        seniority: 'not_stated',
        must_have_skills: [],
        ...change,
    }
}

test('the chips start with the Japanese requirement, then remote policy, seniority and five skills plus the rest counted', () => {
    const chips = postingChips(
        facts({ japanese_required: 'required', remote_policy: 'hybrid', seniority: 'senior', must_have_skills: SKILLS }),
        'business',
    )

    expect(chips).toEqual([
        { kind: 'japanese', label: 'Business Japanese', requirement: 'business' },
        { kind: 'fact', label: 'Hybrid' },
        { kind: 'fact', label: 'Senior' },
        { kind: 'skill', label: 'Go', marked: false },
        { kind: 'skill', label: 'Kubernetes', marked: false },
        { kind: 'skill', label: 'PostgreSQL', marked: false },
        { kind: 'skill', label: 'gRPC', marked: false },
        { kind: 'skill', label: 'Terraform', marked: false },
        { kind: 'more', label: '+2' },
    ])
})

test('facts that are not stated get no chip, and five skills need no count', () => {
    const chips = postingChips(facts({ must_have_skills: SKILLS.slice(0, 5) }), 'not_stated')

    expect(chips).toEqual([
        { kind: 'japanese', label: 'Japanese not stated', requirement: 'not_stated' },
        { kind: 'skill', label: 'Go', marked: false },
        { kind: 'skill', label: 'Kubernetes', marked: false },
        { kind: 'skill', label: 'PostgreSQL', marked: false },
        { kind: 'skill', label: 'gRPC', marked: false },
        { kind: 'skill', label: 'Terraform', marked: false },
    ])
})

test('each remote policy and seniority has its own label', () => {
    const cases: [ChipFacts, JapaneseRequirement][] = [
        [facts({ japanese_required: 'not_required', remote_policy: 'remote', seniority: 'intern' }), 'none'],
        [facts({ japanese_required: 'preferred', remote_policy: 'onsite', seniority: 'junior' }), 'none'],
        [facts({ remote_policy: 'hybrid', seniority: 'mid' }), 'not_stated'],
        [facts({ seniority: 'staff_plus' }), 'not_stated'],
    ]

    expect(cases.map(([chipFacts, requirement]) => postingChips(chipFacts, requirement))).toEqual([
        [
            { kind: 'japanese', label: 'No Japanese', requirement: 'none' },
            { kind: 'fact', label: 'Remote' },
            { kind: 'fact', label: 'Intern' },
        ],
        [
            { kind: 'japanese', label: 'Japanese preferred', requirement: 'none' },
            { kind: 'fact', label: 'On-site' },
            { kind: 'fact', label: 'Junior' },
        ],
        [
            { kind: 'japanese', label: 'Japanese not stated', requirement: 'not_stated' },
            { kind: 'fact', label: 'Hybrid' },
            { kind: 'fact', label: 'Mid-level' },
        ],
        [
            { kind: 'japanese', label: 'Japanese not stated', requirement: 'not_stated' },
            { kind: 'fact', label: 'Staff+' },
        ],
    ])
})

test('the full chips list every skill with no count', () => {
    const chips = allPostingChips(facts({ remote_policy: 'remote', must_have_skills: SKILLS }), 'not_stated')

    expect(chips).toEqual([
        { kind: 'japanese', label: 'Japanese not stated', requirement: 'not_stated' },
        { kind: 'fact', label: 'Remote' },
        { kind: 'skill', label: 'Go', marked: false },
        { kind: 'skill', label: 'Kubernetes', marked: false },
        { kind: 'skill', label: 'PostgreSQL', marked: false },
        { kind: 'skill', label: 'gRPC', marked: false },
        { kind: 'skill', label: 'Terraform', marked: false },
        { kind: 'skill', label: 'AWS', marked: false },
        { kind: 'skill', label: 'Kafka', marked: false },
    ])
})

test('a skill the query matches moves into view past the first five, marked, and the count drops by one', () => {
    const chips = postingChips(facts({ must_have_skills: SKILLS }), 'not_stated', 'kafka engineer')

    expect(chips).toEqual([
        { kind: 'japanese', label: 'Japanese not stated', requirement: 'not_stated' },
        { kind: 'skill', label: 'Go', marked: false },
        { kind: 'skill', label: 'Kubernetes', marked: false },
        { kind: 'skill', label: 'PostgreSQL', marked: false },
        { kind: 'skill', label: 'gRPC', marked: false },
        { kind: 'skill', label: 'Kafka', marked: true },
        { kind: 'more', label: '+2' },
    ])
})

test('a matched skill already in view is marked in place, and every matched skill shows', () => {
    const skills = ['AWS Lambda', 'Go', 'Kubernetes', 'PostgreSQL', 'gRPC', 'Terraform', 'AWS', 'Amazon AWS']

    expect([
        postingChips(facts({ must_have_skills: skills.slice(0, 6) }), 'not_stated', 'go'),
        postingChips(facts({ must_have_skills: skills }), 'not_stated', 'aws'),
    ]).toEqual([
        [
            { kind: 'japanese', label: 'Japanese not stated', requirement: 'not_stated' },
            { kind: 'skill', label: 'AWS Lambda', marked: false },
            { kind: 'skill', label: 'Go', marked: true },
            { kind: 'skill', label: 'Kubernetes', marked: false },
            { kind: 'skill', label: 'PostgreSQL', marked: false },
            { kind: 'skill', label: 'gRPC', marked: false },
            { kind: 'more', label: '+1' },
        ],
        [
            { kind: 'japanese', label: 'Japanese not stated', requirement: 'not_stated' },
            { kind: 'skill', label: 'AWS Lambda', marked: true },
            { kind: 'skill', label: 'Go', marked: false },
            { kind: 'skill', label: 'Kubernetes', marked: false },
            { kind: 'skill', label: 'AWS', marked: true },
            { kind: 'skill', label: 'Amazon AWS', marked: true },
            { kind: 'more', label: '+3' },
        ],
    ])
})
