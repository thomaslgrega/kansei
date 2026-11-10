// Dark enough that a white letter stays readable on each.
const COLORS = ['#b91c1c', '#c2410c', '#a16207', '#15803d', '#0f766e', '#1d4ed8', '#6d28d9', '#be185d']

export function companyTile(name: string): { letter: string; color: string } {
    const characters = [...name.trim()]
    const sum = characters.reduce((total, character) => total + (character.codePointAt(0) ?? 0), 0)
    return { letter: (characters[0] ?? '?').toUpperCase(), color: COLORS[sum % COLORS.length] }
}
