import { type JapaneseFacts, type JapaneseRequirement, japaneseBadge, japaneseRequirement } from './japanese'

export type ChipFacts = JapaneseFacts & {
    remote_policy: string
    seniority: string
    must_have_skills: string[]
}

export type Chip =
    | { kind: 'japanese'; label: string; requirement: JapaneseRequirement }
    | { kind: 'fact' | 'skill' | 'more'; label: string }

const REMOTE_POLICIES = new Map([
    ['remote', 'Remote'],
    ['hybrid', 'Hybrid'],
    ['onsite', 'On-site'],
])

const SENIORITIES = new Map([
    ['intern', 'Intern'],
    ['junior', 'Junior'],
    ['mid', 'Mid-level'],
    ['senior', 'Senior'],
    ['staff_plus', 'Staff+'],
])

const MAX_SKILLS = 5

export function postingChips(facts: ChipFacts): Chip[] {
    return chipsUpTo(facts, MAX_SKILLS)
}

export function allPostingChips(facts: ChipFacts): Chip[] {
    return chipsUpTo(facts, Infinity)
}

function chipsUpTo(facts: ChipFacts, maxSkills: number): Chip[] {
    const chips: Chip[] = [{ kind: 'japanese', label: japaneseBadge(facts), requirement: japaneseRequirement(facts) }]
    for (const label of [REMOTE_POLICIES.get(facts.remote_policy), SENIORITIES.get(facts.seniority)]) {
        if (label) chips.push({ kind: 'fact', label })
    }
    for (const skill of facts.must_have_skills.slice(0, maxSkills)) chips.push({ kind: 'skill', label: skill })
    const rest = facts.must_have_skills.length - maxSkills
    if (rest > 0) chips.push({ kind: 'more', label: `+${rest}` })
    return chips
}
