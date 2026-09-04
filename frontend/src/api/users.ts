import type { UserRole } from '../types/auth'
import type { PlatformUser } from '../types/user'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

function authHeaders(token: string) {
  return {
    Authorization: `Bearer ${token}`,
  }
}

export async function fetchUsers(token: string): Promise<PlatformUser[]> {
  const response = await fetch(`${API_BASE_URL}/users`, {
    headers: authHeaders(token),
  })

  if (!response.ok) {
    throw new Error(`Failed to load users: ${response.status}`)
  }

  return response.json() as Promise<PlatformUser[]>
}

export async function createUser(
  token: string,
  username: string,
  password: string,
  role: UserRole,
): Promise<PlatformUser> {
  const response = await fetch(`${API_BASE_URL}/users`, {
    method: 'POST',
    headers: {
      ...authHeaders(token),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ username, password, role }),
  })

  if (!response.ok) {
    throw new Error(`Failed to create user: ${response.status}`)
  }

  return response.json() as Promise<PlatformUser>
}

export async function updateUser(
  token: string,
  username: string,
  payload: Partial<Pick<PlatformUser, 'role' | 'is_active'>>,
): Promise<PlatformUser> {
  const response = await fetch(`${API_BASE_URL}/users/${username}`, {
    method: 'PATCH',
    headers: {
      ...authHeaders(token),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    throw new Error(`Failed to update user: ${response.status}`)
  }

  return response.json() as Promise<PlatformUser>
}

export async function deleteUser(
  token: string,
  username: string,
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/users/${username}`, {
    method: 'DELETE',
    headers: authHeaders(token),
  })

  if (!response.ok) {
    throw new Error(`Failed to delete user: ${response.status}`)
  }
}
