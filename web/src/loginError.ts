export function loginError(status: number): string {
    return status === 429 ? 'Too many attempts. Try again in a minute.' : 'Wrong email or password'
}
