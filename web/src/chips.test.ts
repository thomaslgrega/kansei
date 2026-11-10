import { expect, test } from 'vitest'
import { type ChipFacts, postingChips } from './chips'

const SKILLS = ['Go', 'Kubernetes', 'PostgreSQL', 'gRPC', 'Terraform', 'AWS', 'Kafka']

function facts(change: Partial<ChipFacts>): ChipFacts {
    return {
        japanese_required: 'not_stated',
        japanese_level: 'not_stated',
        jlpt: 'not_stated',
        remote_policy: 'not_stated',
        seniority: 'not_stated',
        must_have_skills: [],
        ...change,
    }
}

test('the chips start with the Japanese requirement, then remote policy, seniority and five skills plus the rest counted', () => {
    const chips = postingChips(
        facts({ japanese_required: 'required', jlpt: 'N2', remote_policy: 'hybrid', seniority: 'senior', must_have_skills: SKILLS }),
    )

    expect(chips).toEqual([
        { kind: 'japanese', label: 'Business Japanese', requirement: 'business' },
        { kind: 'fact', label: 'Hybrid' },
        { kind: 'fact', label: 'Senior' },
        { kind: 'skill', label: 'Go' },
        { kind: 'skill', label: 'Kubernetes' },
        { kind: 'skill', label: 'PostgreSQL' },
        { kind: 'skill', label: 'gRPC' },
        { kind: 'skill', label: 'Terraform' },
        { kind: 'more', label: '+2' },
    ])
})

test('facts that are not stated get no chip, and five skills need no count', () => {
    const chips = postingChips(facts({ must_have_skills: SKILLS.slice(0, 5) }))

    expect(chips).toEqual([
        { kind: 'japanese', label: 'Japanese not stated', requirement: 'not_stated' },
        { kind: 'skill', label: 'Go' },
        { kind: 'skill', label: 'Kubernetes' },
        { kind: 'skill', label: 'PostgreSQL' },
        { kind: 'skill', label: 'gRPC' },
        { kind: 'skill', label: 'Terraform' },
    ])
})

test('each remote policy and seniority has its own label', () => {
    const cases = [
        facts({ japanese_required: 'not_required', remote_policy: 'remote', seniority: 'intern' }),
        facts({ japanese_required: 'preferred', remote_policy: 'onsite', seniority: 'junior' }),
        facts({ remote_policy: 'hybrid', seniority: 'mid' }),
        facts({ seniority: 'staff_plus' }),
    ]

    expect(cases.map((value) => postingChips(value).map((chip) => chip.label))).toEqual([
        ['No Japanese', 'Remote', 'Intern'],
        ['Japanese preferred', 'On-site', 'Junior'],
        ['Japanese not stated', 'Hybrid', 'Mid-level'],
        ['Japanese not stated', 'Staff+'],
    ])
})
