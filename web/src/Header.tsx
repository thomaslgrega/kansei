import { Link, useLocation } from 'react-router'
import { navLinks } from './navLinks'

type Props = {
    email: string | null
    onLogOut: () => void
}

export default function Header({ email, onLogOut }: Props) {
    const location = useLocation()

    return (
        <header className="site-header">
            <Link to="/" className="brand">kansei</Link>
            <nav aria-label="Main">
                {navLinks(email !== null, location).map((link) => (
                    <Link
                        key={link.label}
                        to={link.to}
                        className={link.look === 'button' ? 'nav-signup' : 'nav-link'}
                        aria-current={link.current ? 'page' : undefined}
                    >
                        {link.label}
                    </Link>
                ))}
            </nav>
            {email !== null && (
                <span className="header-account">
                    {email} · <button onClick={onLogOut}>Log out</button>
                </span>
            )}
        </header>
    )
}
