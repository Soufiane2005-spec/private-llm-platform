import type { UserRole } from '../types/auth'
import type { PlatformUser } from '../types/user'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

function authHeaders(token: string) {
  return {
    Authorization: `Bearer ${token}`,
  }
}

async function readError(
  response: Response,
  fallback: string,
): Promise<string> {
  try {
    const body = (await response.json()) as {
      detail?:
        | string
        | Array<{
            msg?: string
            loc?: Array<string | number>
          }>
    }

    if (typeof body.detail === 'string') {
      return body.detail
    }

    if (Array.isArray(body.detail)) {
      const messages = body.detail
        .map((item) => {
          const location = item.loc?.join('.') ?? ''
          const message = item.msg ?? 'Validation error'

          return location
            ? `${location}: ${message}`
            : message
        })
        .filter(Boolean)

      if (messages.length > 0) {
        return messages.join(' | ')
      }
    }
  } catch {
    // Keep fallback.
  }

  return `${fallback}: ${response.status}`
}

export async function fetchUsers(
  token: string,
): Promise<PlatformUser[]> {
  const response = await fetch(
    `${API_BASE_URL}/users`,
    {
      headers: authHeaders(token),
    },
  )

  if (!response.ok) {
    throw new Error(
      await readError(
        response,
        'Failed to load users',
      ),
    )
  }

  return response.json() as Promise<PlatformUser[]>
}

export async function createUser(
  token: string,
  username: string,
  password: string,
  role: UserRole,
): Promise<PlatformUser> {
  const cleanUsername = username.trim()

  if (!cleanUsername) {
    throw new Error('Username is required.')
  }

  if (password.length < 8) {
    throw new Error(
      'Password must contain at least 8 characters.',
    )
  }

  const response = await fetch(
    `${API_BASE_URL}/users`,
    {
      method: 'POST',
      headers: {
        ...authHeaders(token),
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        username: cleanUsername,
        password,
        role,
      }),
    },
  )

  if (!response.ok) {
    throw new Error(
      await readError(
        response,
        'Failed to create user',
      ),
    )
  }

  return response.json() as Promise<PlatformUser>
}

export async function updateUser(
  token: string,
  username: string,
  payload: Partial<
    Pick<PlatformUser, 'role' | 'is_active'>
  >,
): Promise<PlatformUser> {
  const response = await fetch(
    `${API_BASE_URL}/users/${encodeURIComponent(username)}`,
    {
      method: 'PATCH',
      headers: {
        ...authHeaders(token),
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    },
  )

  if (!response.ok) {
    throw new Error(
      await readError(
        response,
        'Failed to update user',
      ),
    )
  }

  return response.json() as Promise<PlatformUser>
}

export async function deleteUser(
  token: string,
  username: string,
): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/users/${encodeURIComponent(username)}`,
    {
      method: 'DELETE',
      headers: authHeaders(token),
    },
  )

  if (!response.ok) {
    throw new Error(
      await readError(
        response,
        'Failed to delete user',
      ),
    )
  }
}