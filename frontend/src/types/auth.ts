export type UserRole = 'admin' | 'engineer' | 'viewer'

export interface CurrentUser {
  username: string
  role: UserRole
}

export interface LoginResult {
  access_token: string
  token_type: 'bearer'
}
