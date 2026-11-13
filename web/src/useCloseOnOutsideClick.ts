import { type RefObject, useEffect, useEffectEvent } from 'react'

export function useCloseOnOutsideClick(
    open: boolean,
    rootRef: RefObject<HTMLElement | null>,
    triggerRef: RefObject<HTMLElement | null>,
    onClose: () => void,
) {
    const close = useEffectEvent(onClose)

    useEffect(() => {
        if (!open) return
        function closeOutside(event: PointerEvent) {
            if (rootRef.current?.contains(event.target as Node)) return
            close()
            // After the click has moved focus, so a click on another control keeps it.
            setTimeout(() => {
                const focused = document.activeElement
                if (!focused || focused === document.body || rootRef.current?.contains(focused)) triggerRef.current?.focus()
            })
        }
        document.addEventListener('pointerdown', closeOutside)
        return () => document.removeEventListener('pointerdown', closeOutside)
    }, [open, rootRef, triggerRef])
}
