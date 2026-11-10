import { expect, test } from 'vitest'
import { companyTile, shownLogo } from './companyTile'

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

test('a row shows its logo unless there is none or that image failed to load', () => {
    const logo = 'https://example.com/logo.png'

    expect([
        shownLogo(logo, null),
        shownLogo(null, null),
        shownLogo(logo, logo),
        shownLogo(logo, 'https://example.com/old.png'),
    ]).toEqual([logo, null, null, logo])
})
