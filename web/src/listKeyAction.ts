export type ListKeyAction = number | 'pick' | 'close' | null

export function listKeyAction(highlighted: number, key: string, count: number): ListKeyAction {
    switch (key) {
        case 'ArrowDown':
            return Math.min(highlighted + 1, count - 1)
        case 'ArrowUp':
            return Math.max(highlighted - 1, 0)
        case 'Home':
            return 0
        case 'End':
            return count - 1
        case 'Enter':
        case ' ':
            return 'pick'
        case 'Escape':
        case 'Tab':
            return 'close'
        default:
            return null
    }
}
