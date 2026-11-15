import { expect, test } from 'vitest'
import { markQuery, matchesSkill } from './marks'

test('a word is marked where it starts a word, in any case, and not inside one', () => {
    expect(markQuery('Payments on Stripe, not stripes in Pinstripe', 'stripe')).toEqual([
        { text: 'Payments on ', marked: false },
        { text: 'Stripe', marked: true },
        { text: ', not ', marked: false },
        { text: 'stripe', marked: true },
        { text: 's in Pinstripe', marked: false },
    ])
})

test('a word starts after Japanese text, as the search reads it', () => {
    expect(markQuery('シニアRubyエンジニア', 'ruby')).toEqual([
        { text: 'シニア', marked: false },
        { text: 'Ruby', marked: true },
        { text: 'エンジニア', marked: false },
    ])
})

test('a word with Japanese characters is marked anywhere', () => {
    expect(markQuery('React/TypeScriptエンジニア募集', 'エンジニア')).toEqual([
        { text: 'React/TypeScript', marked: false },
        { text: 'エンジニア', marked: true },
        { text: '募集', marked: false },
    ])
})

test('each word of a two-word query is marked, and overlapping marks join', () => {
    expect(markQuery('Go and Golang engineer', 'go golang')).toEqual([
        { text: 'Go', marked: true },
        { text: ' and ', marked: false },
        { text: 'Golang', marked: true },
        { text: ' engineer', marked: false },
    ])
})

test('text with no match is one unmarked segment, and an empty query marks nothing', () => {
    expect([markQuery('Backend Engineer', 'stripe'), markQuery('Backend Engineer', ''), markQuery('', 'go')]).toEqual([
        [{ text: 'Backend Engineer', marked: false }],
        [{ text: 'Backend Engineer', marked: false }],
        [],
    ])
})

test('a word is matched as written, so regex characters in it are plain', () => {
    expect(markQuery('C++ or C, not C.', 'c++ c.')).toEqual([
        { text: 'C++', marked: true },
        { text: ' or C, not ', marked: false },
        { text: 'C.', marked: true },
    ])
})

test('a skill matches a word equal to one of its words, or containing a Japanese word', () => {
    const cases: [string, string][] = [
        ['React Native', 'react'],
        ['TypeScript', 'type'],
        ['Go', 'GO'],
        ['AWS', 'stripe aws'],
        ['日本語能力', '日本語'],
        ['Go', ''],
    ]

    expect(cases.map(([skill, query]) => matchesSkill(skill, query))).toEqual([true, false, true, true, true, false])
})
