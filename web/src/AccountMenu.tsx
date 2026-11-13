import { useEffect, useId, useRef, useState } from 'react'
import { useCloseOnOutsideClick } from './useCloseOnOutsideClick'

type Props = {
    email: string
    onLogOut: () => void
}

export default function AccountMenu({ email, onLogOut }: Props) {
    const panelId = useId()
    const [open, setOpen] = useState(false)
    const rootRef = useRef<HTMLDivElement>(null)
    const triggerRef = useRef<HTMLButtonElement>(null)

    useCloseOnOutsideClick({ open, rootRef, triggerRef, onClose: () => setOpen(false) })

    // On the document, since Safari leaves focus on the body after a click on the trigger.
    useEffect(() => {
        if (!open) return
        function closeOnEscape(event: KeyboardEvent) {
            if (event.key !== 'Escape') return
            event.preventDefault()
            setOpen(false)
            triggerRef.current?.focus()
        }
        document.addEventListener('keydown', closeOnEscape)
        return () => document.removeEventListener('keydown', closeOnEscape)
    }, [open])

    return (
        <div className="account-menu" ref={rootRef}>
            <button
                ref={triggerRef}
                type="button"
                className="account-trigger"
                aria-expanded={open}
                aria-controls={panelId}
                onClick={() => setOpen(!open)}
            >
                Account
                <svg className="dropdown-chevron" viewBox="0 0 12 12" aria-hidden="true">
                    <path d="M2.5 4.5 6 8l3.5-3.5" />
                </svg>
            </button>
            <div id={panelId} className="account-panel" hidden={!open}>
                <p className="account-who">
                    <span className="muted">Signed in as</span>
                    <strong>{email}</strong>
                </p>
                <button type="button" className="account-item" onClick={onLogOut}>
                    Log out
                </button>
            </div>
        </div>
    )
}
