export const SPECIALTY_CHOICES = [
    ['backend', 'Backend'],
    ['frontend', 'Frontend'],
    ['mobile', 'Mobile'],
    ['infrastructure', 'Infrastructure'],
    ['data', 'Data'],
    ['ml', 'ML / AI'],
    ['security', 'Security'],
    ['qa', 'QA / Test'],
    ['embedded', 'Embedded / Hardware'],
    ['management', 'Management'],
    ['customer_facing', 'Sales & Support'],
    ['other', 'Other'],
] as const

export type SpecialtyChoice = (typeof SPECIALTY_CHOICES)[number][0]

// null: no param, every specialty. []: the user cleared them all.
export type Selected = SpecialtyChoice[] | null

function normalize(values: readonly string[]): Selected {
    const picked = SPECIALTY_CHOICES.map(([choice]) => choice).filter((choice) => values.includes(choice))
    return picked.length === SPECIALTY_CHOICES.length ? null : picked
}

export function readSpecialties(param: string | null): Selected {
    return param === null ? null : normalize(param.split(','))
}

export function specialtiesParam(selected: Selected): string | null {
    const picked = selected && normalize(selected)
    return picked && picked.join(',')
}

export function specialtyLabel(selected: Selected): string {
    if (selected === null) return 'All'
    if (selected.length === 0) return 'None'
    if (selected.length > 2) return `${selected.length} selected`
    return SPECIALTY_CHOICES.filter(([choice]) => selected.includes(choice)).map(([, label]) => label).join(', ')
}

export function isTicked(selected: Selected, choice: SpecialtyChoice): boolean {
    return selected === null || selected.includes(choice)
}

export function toggleSpecialty(selected: Selected, choice: SpecialtyChoice): Selected {
    const ticked = SPECIALTY_CHOICES.map(([value]) => value).filter((value) => isTicked(selected, value))
    return normalize(isTicked(selected, choice) ? ticked.filter((value) => value !== choice) : [...ticked, choice])
}
