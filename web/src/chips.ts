import { type JapaneseRequired, type JapaneseRequirement, japaneseBadge } from './japanese'
import { matchesSkill } from './marks'

export type ChipFacts = {
    japanese_required: JapaneseRequired
    remote_policy: string
    seniority: string
    must_have_skills: string[]
}

export type Chip =
    | { kind: 'japanese'; label: string; requirement: JapaneseRequirement }
    | { kind: 'skill'; label: string; marked: boolean }
    | { kind: 'fact' | 'more'; label: string }

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

export function postingChips(facts: ChipFacts, requirement: JapaneseRequirement, query = ''): Chip[] {
    return chipsUpTo(facts, requirement, MAX_SKILLS, query)
}

export function allPostingChips(facts: ChipFacts, requirement: JapaneseRequirement): Chip[] {
    return chipsUpTo(facts, requirement, Infinity, '')
}

function chipsUpTo(facts: ChipFacts, requirement: JapaneseRequirement, maxSkills: number, query: string): Chip[] {
    const label = japaneseBadge(requirement, facts.japanese_required)
    const chips: Chip[] = [{ kind: 'japanese', label, requirement }]
    for (const label of [REMOTE_POLICIES.get(facts.remote_policy), SENIORITIES.get(facts.seniority)]) {
        if (label) chips.push({ kind: 'fact', label })
    }
    const skills = facts.must_have_skills.map((skill) => ({ kind: 'skill' as const, label: skill, marked: matchesSkill(skill, query) }))
    const fillers = skills.filter((skill) => !skill.marked).slice(0, maxSkills - skills.filter((skill) => skill.marked).length)
    const shown = skills.filter((skill) => skill.marked || fillers.includes(skill))
    chips.push(...shown)
    const rest = skills.length - shown.length
    if (rest > 0) chips.push({ kind: 'more', label: `+${rest}` })
    return chips
}
