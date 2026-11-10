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
                <span>
                    <Link to={loginHref(location)}>Log in</Link> · <Link to="/signup">Sign up</Link>
                </span>
            ) : (
                <span>
                    <Link to="/following">Following</Link> · <Link to="/tracked">Tracked</Link> · {email} · <button onClick={onLogOut}>Log out</button>
                </span>
            )}
        </header>
    )
}
