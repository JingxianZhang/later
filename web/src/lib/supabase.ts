// To keep the prototype stable without enforcing auth deps,
// default to no-op Supabase client. When ready, switch to
// '@supabase/supabase-js' and create a real client.
export const supabase = null as any

export function setUserIdLocal(userId: string | null) {
  if (userId) {
    localStorage.setItem('USER_ID', userId)
  } else {
    localStorage.removeItem('USER_ID')
  }
}

export function getUserIdLocal(): string | null {
  return localStorage.getItem('USER_ID')
}

export function ensureAnonymousUserId(): string {
  let id = getUserIdLocal()
  if (!id) {
    try {
      id = crypto.randomUUID()
    } catch {
      // fallback: timestamp-based
      id = 'anon-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 8)
    }
    setUserIdLocal(id)
  }
  return id!
}


