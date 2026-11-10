import { expect, test } from 'vitest'
import { signupError } from './signupError'

const invalid = (field: string, type: string) => ({ detail: [{ type, loc: ['body', field] }] })

test('each rejected signup gets its own message', () => {
    const failures: [number, unknown][] = [
        [409, { detail: 'Email already registered' }],
        [422, invalid('password', 'string_too_short')],
        [422, invalid('password', 'string_too_long')],
        [422, invalid('email', 'value_error')],
        [429, { detail: 'Too many attempts. Try again later.' }],
        [500, null],
    ]

    expect(failures.map(([status, body]) => signupError(status, body))).toEqual([
        'That email is already registered. Log in instead.',
        'The password needs at least 15 characters.',
        'The password can be at most 128 characters.',
        "That doesn't look like an email address.",
        'Too many signups from here. Try again later.',
        'Something went wrong. Try again.',
    ])
})
