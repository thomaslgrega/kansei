import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router'
import { loginHref } from './loginRedirect'

type Props = {
    loggedIn: boolean
    children: ReactNode
}

export default function RequireLogin({ loggedIn, children }: Props) {
    const location = useLocation()
    return loggedIn ? children : <Navigate to={loginHref(location)} replace />
}
