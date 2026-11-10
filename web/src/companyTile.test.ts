import { expect, test } from 'vitest'
import { companyTile } from './companyTile'

test("a company's tile is the first letter of its name on a color picked from the name", () => {
    const names = ['Stripe', 'mercari', 'Woven by Toyota', 'ビジョナル株式会社', '  Stripe']

    expect(names.map(companyTile)).toEqual([
        { letter: 'S', color: '#be185d' },
        { letter: 'M', color: '#15803d' },
        { letter: 'W', color: '#a16207' },
        { letter: 'ビ', color: '#b91c1c' },
        { letter: 'S', color: '#be185d' },
    ])
})
