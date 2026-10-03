/**
 * utils/session.ts
 * Manages anonymous session_id strictly without PII, tracking, or persistent telemetry.
 * Web: Uses sessionStorage only.
 */

const SESSION_KEY = 'sellsmart_session_id';

let memorySessionId: string | null = null;

function generateUUID(): string {
  return 'sess_' + Math.random().toString(36).substring(2, 11) + '_' + Date.now();
}

export function getOrCreateSessionId(): string {
  if (typeof window !== 'undefined' && window.sessionStorage) {
    let id = window.sessionStorage.getItem(SESSION_KEY);
    if (!id) {
      id = generateUUID();
      window.sessionStorage.setItem(SESSION_KEY, id);
    }
    return id;
  }

  if (!memorySessionId) {
    memorySessionId = generateUUID();
  }
  return memorySessionId;
}

export function clearSession(): void {
  if (typeof window !== 'undefined' && window.sessionStorage) {
    window.sessionStorage.removeItem(SESSION_KEY);
  }
  memorySessionId = null;
}
