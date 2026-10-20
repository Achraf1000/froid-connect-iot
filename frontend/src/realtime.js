import { initializeApp, deleteApp } from 'firebase/app'
import { connectAuthEmulator, getAuth, inMemoryPersistence, setPersistence, signInWithCustomToken, signOut } from 'firebase/auth'
import { connectDatabaseEmulator, getDatabase, onValue, ref } from 'firebase/database'

export async function subscribeTransport(transportId, onState, onError) {
  const response = await fetch('/api/v1/firebase/session', { credentials: 'include' })
  if (!response.ok) throw new Error('Temps réel indisponible')
  const session = await response.json()
  const app = initializeApp(session.config, `transport-${crypto.randomUUID()}`)
  const auth = getAuth(app)
  const db = getDatabase(app)
  try {
    if (session.mode === 'emulator') {
      connectAuthEmulator(auth, session.auth_url, { disableWarnings: true })
      connectDatabaseEmulator(db, session.database_host, session.database_port)
    }
    await setPersistence(auth, inMemoryPersistence)
    await signInWithCustomToken(auth, session.token)
    const unsubscribe = onValue(ref(db, `transports/${transportId}/state`), snap => {
      if (snap.exists()) onState(snap.val())
    }, onError)
    return () => { unsubscribe(); signOut(auth).finally(() => deleteApp(app)) }
  } catch (error) {
    await deleteApp(app)
    throw error
  }
}
