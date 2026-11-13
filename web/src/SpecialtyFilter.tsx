import { type FocusEvent, type KeyboardEvent, useEffect, useId, useRef, useState } from 'react'
import { isTicked, type Selected, SPECIALTY_CHOICES, specialtyLabel, toggleSpecialty } from './specialty'

type Props = {
    selected: Selected
    onChange: (selected: Selected) => void
}

export default function SpecialtyFilter({ selected, onChange }: Props) {
    const id = useId()
    const labelId = `${id}-label`
    const listId = `${id}-list`
    const [open, setOpen] = useState(false)
    const rootRef = useRef<HTMLDivElement>(null)
    const triggerRef = useRef<HTMLButtonElement>(null)

    useEffect(() => {
        if (!open) return
        function closeOutside(event: PointerEvent) {
            if (!rootRef.current?.contains(event.target as Node)) setOpen(false)
        }
        document.addEventListener('pointerdown', closeOutside)
        return () => document.removeEventListener('pointerdown', closeOutside)
    }, [open])

    function onKeyDown(event: KeyboardEvent) {
        if (!open || event.key !== 'Escape') return
        event.preventDefault()
        setOpen(false)
        triggerRef.current?.focus()
    }

    function onBlur(event: FocusEvent) {
        if (!rootRef.current?.contains(event.relatedTarget)) setOpen(false)
    }

    return (
        <div className="dropdown" ref={rootRef} onKeyDown={onKeyDown} onBlur={onBlur}>
            <button
                ref={triggerRef}
                type="button"
                className="dropdown-trigger"
                aria-expanded={open}
                aria-controls={listId}
                onClick={() => setOpen(!open)}
            >
                <span id={labelId} className="muted">
                    Specialty
                </span>
                <span className="dropdown-value">{specialtyLabel(selected)}</span>
                <svg className="dropdown-chevron" viewBox="0 0 12 12" aria-hidden="true">
                    <path d="M2.5 4.5 6 8l3.5-3.5" />
                </svg>
            </button>
            <div id={listId} className="dropdown-list checklist" role="group" aria-labelledby={labelId} hidden={!open}>
                <div className="checklist-actions">
                    <button type="button" className="link-button" onClick={() => onChange(null)}>
                        Select all
                    </button>
                    <button type="button" className="link-button" onClick={() => onChange([])}>
                        Clear
                    </button>
                </div>
                {SPECIALTY_CHOICES.map(([choice, label]) => (
                    <label key={choice} className="dropdown-option checklist-option">
                        <input
                            type="checkbox"
                            checked={isTicked(selected, choice)}
                            onChange={() => onChange(toggleSpecialty(selected, choice))}
                        />
                        {label}
                    </label>
                ))}
            </div>
        </div>
    )
}
