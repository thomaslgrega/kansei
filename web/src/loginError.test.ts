import { expect, test } from 'vitest'
import { loginError } from './loginError'

test('a rate-limited login says to wait, any other failure says the credentials are wrong', () => {
    expect([429, 401, 422].map(loginError)).toEqual([
        'Too many attempts. Try again in a minute.',
        'Wrong email or password',
        'Wrong email or password',
    ])
})
