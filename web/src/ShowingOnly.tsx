export default function ShowingOnly({ company, onShowAll }: { company: string; onShowAll: () => void }) {
    return (
        <p className="following-selected">
            Showing only <strong>{company}</strong> ·{' '}
            <button className="link-button" onClick={onShowAll}>
                Show all
            </button>
        </p>
    )
}
