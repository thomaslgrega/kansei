export type Segment = { text: string; marked: boolean }

// The same characters as CJK in src/kansei/search.py.
const JAPANESE = /[々぀-ヿㇰ-ㇿ㐀-䶿一-鿿豈-﫿ｦ-ﾟ]/

function escape(word: string): string {
    return word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function wordPattern(word: string): RegExp {
    if (JAPANESE.test(word)) return new RegExp(escape(word), 'giu')
    return new RegExp(`(?<![0-9a-z\\u00c0-\\u024f_])${escape(word)}`, 'giu')
}

export function markQuery(text: string, query: string): Segment[] {
    const marked = new Array<boolean>(text.length).fill(false)
    for (const word of query.split(/\s+/).filter(Boolean)) {
        for (const match of text.matchAll(wordPattern(word))) marked.fill(true, match.index, match.index + match[0].length)
    }
    const segments: Segment[] = []
    for (let start = 0, end = 1; start < text.length; end++) {
        if (end === text.length || marked[end] !== marked[start]) {
            segments.push({ text: text.slice(start, end), marked: marked[start] })
            start = end
        }
    }
    return segments
}

export function matchesSkill(skill: string, query: string): boolean {
    const skillWords = skill.toLowerCase().split(' ')
    return query.split(/\s+/).filter(Boolean).some((word) =>
        JAPANESE.test(word) ? skill.toLowerCase().includes(word.toLowerCase()) : skillWords.includes(word.toLowerCase()),
    )
}
