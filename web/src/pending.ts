type SetPending<K> = (update: (current: Set<K>) => Set<K>) => void

export async function whilePending<K>(setPending: SetPending<K>, key: K, work: () => Promise<void>): Promise<void> {
    setPending((current) => new Set(current).add(key))
    try {
        await work()
    } finally {
        setPending((current) => {
            const next = new Set(current)
            next.delete(key)
            return next
        })
    }
}
