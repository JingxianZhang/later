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
  // If missing or not a valid UUID, create a UUID v4 so backend UUID casts work
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
  if (!id || !uuidRegex.test(id)) {
    let newId: string
    try {
      // crypto.randomUUID is unavailable on some older browsers or non-secure contexts
      newId = (crypto as any)?.randomUUID?.() as string
    } catch {
      newId = ''
    }
    if (!newId) {
      // Generate UUID v4 using Math.random (sufficient for anonymous client id)
      newId = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
        const r = (Math.random() * 16) | 0
        const v = c === 'x' ? r : (r & 0x3) | 0x8
        return v.toString(16)
      })
    }
    id = newId
    setUserIdLocal(id)
  }
  return id!
}


