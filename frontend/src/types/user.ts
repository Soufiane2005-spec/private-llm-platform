import type { UserRole } from './auth'

export interface PlatformUser {
  username: string
  role: UserRole
  is_active: boolean
}
