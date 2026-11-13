import { loginHref, type Place } from './loginRedirect'

export type NavLink = {
    label: string
    to: string
    look: 'link' | 'button'
    current: boolean
}

export function navLinks(loggedIn: boolean, place: Place): NavLink[] {
    const link = (label: string, to: string, look: NavLink['look'] = 'link', path = to): NavLink => ({
        label,
        to,
        look,
        current: place.pathname === path,
    })

    if (!loggedIn) {
        return [link('Log in', loginHref(place), 'link', '/login'), link('Sign up', '/signup', 'button')]
    }
    return [link('Postings', '/'), link('Following', '/following'), link('Tracker', '/tracker')]
}
