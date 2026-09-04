import type { CurrentUser, LoginResult } from '../types/auth'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export async function login(
  username: string,
  password: string,
): Promise<LoginResult> {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ username, password }),
  })

  if (!response.ok) {
    throw new Error(`Login failed: ${response.status}`)
  }

  return response.json() as Promise<LoginResult>
}

export async function fetchCurrentUser(token: string): Promise<CurrentUser> {
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  if (!response.ok) {
    throw new Error(`Failed to load user: ${response.status}`)
  }

  return response.json() as Promise<CurrentUser>
}
