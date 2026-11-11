import { type KeyboardEvent, useEffect, useId, useRef, useState } from 'react'
import { listKeyAction } from './listKeyAction'

export type DropdownOption<T extends string> = {
    value: T
    label: string
    hint?: string
}

type Props<T extends string> = {
    label: string
    options: DropdownOption<T>[]
    value: T
    onChange: (value: T) => void
}

export default function Dropdown<T extends string>({ label, options, value, onChange }: Props<T>) {
    const id = useId()
    const labelId = `${id}-label`
    const listId = `${id}-list`
    const optionId = (index: number) => `${id}-${index}`
    const [highlighted, setHighlighted] = useState<number | null>(null)
    const open = highlighted !== null
    const rootRef = useRef<HTMLDivElement>(null)
    const triggerRef = useRef<HTMLButtonElement>(null)
    const listRef = useRef<HTMLUListElement>(null)
    const selectedIndex = options.findIndex((option) => option.value === value)

    function openList() {
        setHighlighted(Math.max(selectedIndex, 0))
    }

    function close() {
        setHighlighted(null)
        triggerRef.current?.focus()
    }

    function pick(index: number) {
        onChange(options[index].value)
        close()
    }

    useEffect(() => {
        if (!open) return
        listRef.current?.focus()
        function closeOutside(event: PointerEvent) {
            if (rootRef.current?.contains(event.target as Node)) return
            setHighlighted(null)
            // After the click has moved focus, so a click on another control keeps it.
            setTimeout(() => {
                const focused = document.activeElement
                if (!focused || focused === document.body || rootRef.current?.contains(focused)) triggerRef.current?.focus()
            })
        }
        document.addEventListener('pointerdown', closeOutside)
        return () => document.removeEventListener('pointerdown', closeOutside)
    }, [open])

    function onTriggerKeyDown(event: KeyboardEvent) {
        if (!open && (event.key === 'ArrowDown' || event.key === 'ArrowUp')) {
            event.preventDefault()
            openList()
        }
    }

    function onListKeyDown(event: KeyboardEvent) {
        if (highlighted === null) return
        const result = listKeyAction(highlighted, event.key, options.length)
        if (result === null) return
        // Tab still moves focus on, from the trigger.
        if (event.key !== 'Tab') event.preventDefault()
        if (result === 'pick') pick(highlighted)
        else if (result === 'close') close()
        else setHighlighted(result)
    }

    return (
        <div className="dropdown" ref={rootRef}>
            <button
                ref={triggerRef}
                type="button"
                className="dropdown-trigger"
                aria-haspopup="listbox"
                aria-expanded={open}
                aria-controls={listId}
                onClick={() => (open ? close() : openList())}
                onKeyDown={onTriggerKeyDown}
            >
                <span id={labelId} className="muted">
                    {label}
                </span>
                <span className="dropdown-value">{options[selectedIndex]?.label}</span>
                <svg className="dropdown-chevron" viewBox="0 0 12 12" aria-hidden="true">
                    <path d="M2.5 4.5 6 8l3.5-3.5" />
                </svg>
            </button>
            <ul
                ref={listRef}
                id={listId}
                className="dropdown-list"
                role="listbox"
                tabIndex={-1}
                aria-labelledby={labelId}
                aria-activedescendant={open ? optionId(highlighted) : undefined}
                hidden={!open}
                onKeyDown={onListKeyDown}
            >
                {options.map((option, index) => (
                    <li
                        key={option.value}
                        id={optionId(index)}
                        role="option"
                        aria-selected={index === selectedIndex}
                        className={index === highlighted ? 'dropdown-option highlighted' : 'dropdown-option'}
                        onMouseEnter={() => setHighlighted(index)}
                        onClick={() => pick(index)}
                    >
                        <span className="dropdown-option-label">{option.label}</span>
                        {option.hint && <span className="dropdown-option-hint muted">{option.hint}</span>}
                    </li>
                ))}
            </ul>
        </div>
    )
}
