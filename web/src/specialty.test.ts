import { expect, test } from 'vitest'
import { readSpecialties, type Selected, SPECIALTY_CHOICES, specialtiesParam, specialtyLabel, toggleSpecialty } from './specialty'

const ALL = 'backend,frontend,mobile,infrastructure,data,ml,security,qa,embedded,management,customer_facing,other'

test('reads every specialty from no param or all 12, and drops unknown values', () => {
    const params = [null, 'ml,backend', ALL, `${ALL},bogus`, '', 'bogus', 'bogus,ml,ml', 'fullstack']

    expect(params.map(readSpecialties)).toEqual([
        null,
        ['backend', 'ml'],
        null,
        null,
        [],
        [],
        ['ml'],
        [],
    ])
})

test('writes picks in list order, an empty param once cleared, and no param for every specialty', () => {
    const every = SPECIALTY_CHOICES.map(([choice]) => choice)
    const selections: Selected[] = [null, ['ml', 'backend'], every, [], ['other']]

    expect(selections.map(specialtiesParam)).toEqual([
        null,
        'backend,ml',
        null,
        '',
        'other',
    ])
})

test('the button names one or two picks and counts more', () => {
    const selections: Selected[] = [null, [], ['ml'], ['ml', 'backend'], ['backend', 'ml', 'other']]

    expect(selections.map(specialtyLabel)).toEqual([
        'All',
        'None',
        'ML / AI',
        'Backend, ML / AI',
        '3 selected',
    ])
})

test('toggling starts from every specialty and gives no filter once all 12 are ticked', () => {
    const allButBackend = ALL.split(',').filter((choice) => choice !== 'backend')

    expect([
        toggleSpecialty(null, 'backend'),
        toggleSpecialty(['ml'], 'backend'),
        toggleSpecialty(['ml'], 'ml'),
        toggleSpecialty(readSpecialties(allButBackend.join(',')), 'backend'),
    ]).toEqual([allButBackend, ['backend', 'ml'], [], null])
})
