type Props = {
    onUntrack: () => void
    onKeep: () => void
}

export default function UntrackConfirm({ onUntrack, onKeep }: Props) {
    return (
        <span className="untrack-confirm">
            Untracking deletes its stage and note.
            <button type="button" className="untrack" onClick={onUntrack}>
                Untrack
            </button>
            <button type="button" className="keep" onClick={onKeep}>
                Keep
            </button>
        </span>
    )
}
