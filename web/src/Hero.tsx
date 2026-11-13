import { Link } from 'react-router'

function browsePostings() {
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    document.getElementById('postings')?.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth' })
}

export default function Hero() {
    return (
        <section className="hero">
            <h1>Engineering jobs you can do from&nbsp;Japan.</h1>
            <p className="hero-lead">Each posting shows the Japanese level it asks for, so you can filter out the ones that need more than you have.</p>
            <div className="hero-actions">
                <button className="hero-primary" onClick={browsePostings}>Browse postings</button>
                <Link to="/signup" className="hero-secondary">Sign up</Link>
            </div>
            <p className="hero-note muted">An account lets you track applications and follow companies.</p>
        </section>
    )
}
