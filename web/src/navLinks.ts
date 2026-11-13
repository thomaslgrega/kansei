import { loginHref } from './loginRedirect'

type Place = { pathname: string; search: string; hash: string }

export type NavLink = {
    label: string
    to: string
    look: 'link' | 'button'
    current: boolean
}

export function navLinks(loggedIn: boolean, place: Place): NavLink[] {
    const link = (label: string, to: string, path: string, look: NavLink['look'] = 'link'): NavLink => ({
        label,
        to,
        look,
        current: place.pathname === path,
    })

    if (!loggedIn) {
        return [link('Log in', loginHref(place), '/login'), link('Sign up', '/signup', '/signup', 'button')]
    }
    return [link('Postings', '/', '/'), link('Following', '/following', '/following'), link('Tracker', '/tracker', '/tracker')]
}
