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

function queryWords(query: string): string[] {
    return query.split(/\s+/).filter(Boolean)
}

export function markQuery(text: string, query: string): Segment[] {
    const marked = new Array<boolean>(text.length).fill(false)
    for (const word of queryWords(query)) {
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
    const lower = skill.toLowerCase()
    return queryWords(query.toLowerCase()).some((word) => (JAPANESE.test(word) ? lower.includes(word) : lower.split(' ').includes(word)))
}
