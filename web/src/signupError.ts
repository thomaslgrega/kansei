type Problem = { type?: string; loc?: unknown[] }

function firstProblem(body: unknown): Problem {
    const detail = (body as { detail?: unknown } | null)?.detail
    return Array.isArray(detail) && detail.length > 0 ? detail[0] : {}
}

export function signupError(status: number, body: unknown): string {
    if (status === 409) return 'That email is already registered. Log in instead.'
    if (status === 429) return 'Too many signups from here. Try again later.'
    if (status === 422) {
        const problem = firstProblem(body)
        if (problem.loc?.at(-1) === 'email') return "That doesn't look like an email address."
        return problem.type === 'string_too_long'
            ? 'The password can be at most 128 characters.'
            : 'The password needs at least 15 characters.'
    }
    return 'Something went wrong. Try again.'
}
