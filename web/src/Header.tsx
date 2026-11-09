import { Link, useLocation } from 'react-router'
import { loginHref } from './loginRedirect'

type Props = {
    email: string | null
    onLogOut: () => void
}

export default function Header({ email, onLogOut }: Props) {
    const location = useLocation()

    return (
        <header>
            <Link to="/" className="brand">kansei</Link>
            {email === null ? (
                <Link to={loginHref(location)}>Log in</Link>
            ) : (
                <span>
                    {email} · <button onClick={onLogOut}>Log out</button>
                </span>
            )}
        </header>
    )
}
