import React, { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import {
  Activity, ArrowDownToLine, ArrowRight, Bell, Check, ChevronRight, Clock3,
  Database, LayoutDashboard, LogOut, MapPin, Plus, Radio, Route, ShieldCheck,
  Snowflake, Thermometer, Truck, Wifi, WifiOff, X,
} from 'lucide-react'
import {
  Area, CartesianGrid, ComposedChart, ReferenceArea, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { CircleMarker, MapContainer, Polyline, Popup, TileLayer, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import './style.css'
import { subscribeTransport } from './realtime'

const labels = {
  normal: 'Dans la plage', pending: 'Dépassement en cours',
  alert: 'Alerte thermique', sensor_error: 'Erreur du capteur',
}
const date = (value, options = {}) => value
  ? new Date(value).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit', ...options }) : '—'
const temperature = value => value == null ? '—' : value.toLocaleString('fr-FR', { maximumFractionDigits: 2 })
async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: 'include', headers: { 'Content-Type': 'application/json' }, ...options,
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    const error = new Error(typeof body.detail === 'string' ? body.detail : 'La requête n’a pas abouti.')
    error.status = response.status
    throw error
  }
  return response.json()
}

function Login({ onLogin }) {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  async function submit(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      await api('/api/v1/auth/login', { method: 'POST', body: JSON.stringify({ password }) })
      onLogin()
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }
  return <div className="login">
    <div className="login-story">
      <div className="brand"><Snowflake size={32} /><span>froid<span className="brand-light">connect</span></span></div>
      <div><span className="eyebrow">CHAÎNE DU FROID INTELLIGENTE</span>
        <h1>Chaque degré<br />compte.</h1>
        <p>La température, le trajet et les événements de votre transport, au même endroit.</p>
        <div className="login-route"><span><MapPin size={18} /> Tunis</span><div /><Truck size={24} /><div /><span>La Marsa</span></div>
      </div>
      <span className="subtle">Projet IoT · Achraf Abdelhedi</span>
    </div>
    <div className="login-panel"><form onSubmit={submit}>
      <span className="icon-box"><ShieldCheck size={26} /></span>
      <h2>Votre espace de supervision</h2>
      <p>Connectez-vous pour suivre le transport et consulter son historique.</p>
      <label htmlFor="password">Mot de passe du tableau de bord</label>
      <input id="password" autoComplete="current-password" type="password" value={password} onChange={e => setPassword(e.target.value)} required autoFocus />
      {error && <p role="alert" className="error-text">{error}</p>}
      <button className="button primary" disabled={busy}>{busy ? 'Connexion…' : 'Se connecter'}<ArrowRight size={18} /></button>
      <small>Prototype pédagogique · Données de transport simulées</small>
    </form></div>
  </div>
}

function FollowVehicle({ position, path }) {
  const map = useMap()
  useEffect(() => {
    if (path.length > 1) map.fitBounds(path, { padding: [35, 35], maxZoom: 14 })
    else if (position) map.setView(position, 13)
  }, [map, path.length, position?.[0], position?.[1]])
  return null
}

function TemperatureChart({ rows }) {
  const data = [...rows].reverse().map(m => ({
    time: new Date(m.measured_at || m.received_at).getTime(), temperature: m.temperature_c,
  }))
  if (!data.length) return <div className="empty chart-empty"><Activity size={32} /><strong>En attente des premières mesures</strong><span>La courbe apparaîtra dès la réception du capteur.</span></div>
  return <ResponsiveContainer width="100%" height={265}>
    <ComposedChart data={data} margin={{ top: 12, right: 16, left: -24, bottom: 5 }}>
      <defs><linearGradient id="temperatureFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#159b98" stopOpacity={0.18} /><stop offset="100%" stopColor="#159b98" stopOpacity={0.01} /></linearGradient></defs>
      <CartesianGrid stroke="#edf1f3" vertical={false} />
      <XAxis dataKey="time" type="number" domain={['dataMin', 'dataMax']} tickFormatter={v => date(v, { second: undefined })} tickLine={false} axisLine={false} minTickGap={35} tick={{ fontSize: 11, fill: '#81909c' }} />
      <YAxis domain={[min => Math.min(0, min - 1), max => Math.max(10, max + 1)]} tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: '#81909c' }} />
      <ReferenceArea y1={2} y2={8} fill="#e8f6ed" fillOpacity={0.6} />
      <ReferenceLine y={8} stroke="#b4cebf" strokeDasharray="4 4" label={{ value: '8 °C', position: 'insideTopRight', fill: '#7c9685', fontSize: 11 }} />
      <ReferenceLine y={2} stroke="#b4cebf" strokeDasharray="4 4" />
      <Tooltip labelFormatter={v => date(v)} formatter={v => [`${temperature(v)} °C`, 'Température']} contentStyle={{ border: '1px solid #e6ecef', borderRadius: 10, fontSize: 12 }} />
      <Area type="linear" dataKey="temperature" stroke="#139a97" strokeWidth={2.5} fill="url(#temperatureFill)" connectNulls={false} isAnimationActive={false} />
    </ComposedChart>
  </ResponsiveContainer>
}

function NewTransport({ onClose, onCreated }) {
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  return <div className="modal-backdrop" onClick={onClose}><form className="modal" onClick={e => e.stopPropagation()} onSubmit={async e => {
    e.preventDefault(); setBusy(true)
    try {
      const item = await api('/api/v1/transports', { method: 'POST', body: JSON.stringify({
        id: `TRIP-${Date.now()}`, name, origin: 'Tunis', destination: 'La Marsa',
      }) })
      onCreated(item)
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }}>
    <button className="icon-button close" type="button" onClick={onClose} aria-label="Fermer"><X /></button>
    <span className="icon-box"><Truck /></span><h2>Nouveau transport</h2>
    <p>Le trajet de démonstration relie Tunis à La Marsa.</p>
    <label htmlFor="transport-name">Nom du transport</label>
    <input id="transport-name" value={name} onChange={e => setName(e.target.value)} maxLength={100} required placeholder="Ex. Livraison du matin" autoFocus />
    <small>Après création, utilisez son identifiant dans la configuration du simulateur.</small>
    {error && <p className="error-text" role="alert">{error}</p>}
    <button className="button primary" disabled={busy}>Créer le transport<ArrowRight size={16} /></button>
  </form></div>
}

function Dashboard({ onLogout }) {
  const [tab, setTab] = useState('overview')
  const [transports, setTransports] = useState([])
  const [selected, setSelected] = useState('')
  const [snapshot, setSnapshot] = useState(null)
  const [rows, setRows] = useState([])
  const [total, setTotal] = useState(0)
  const [alerts, setAlerts] = useState([])
  const [services, setServices] = useState(null)
  const [error, setError] = useState('')
  const [newTransport, setNewTransport] = useState(false)
  const [filter, setFilter] = useState('all')
  const [tick, setTick] = useState(Date.now())
  const [actionError, setActionError] = useState('')
  const [page, setPage] = useState(0)
  const [history, setHistory] = useState([])
  const [tileError, setTileError] = useState(false)
  const [realtime, setRealtime] = useState(false)
  useEffect(() => {
    if (!selected) return
    let cancelled = false, cleanup
    setRealtime(false)
    subscribeTransport(selected, value => {
      if (!cancelled) {
        setRealtime(true)
        setSnapshot(previous => {
          // An old Firebase publication must not overwrite a newer API snapshot.
          if (previous?.state && previous.state.received_at > value.received_at) return previous
          return { ...previous, state: value }
        })
      }
    }, () => { if (!cancelled) setRealtime(false) })
      .then(stop => { if (cancelled) stop(); else cleanup = stop })
      .catch(() => { if (!cancelled) setRealtime(false) })
    return () => { cancelled = true; cleanup?.() }
  }, [selected])
  useEffect(() => { const id = setInterval(() => setTick(Date.now()), 1000); return () => clearInterval(id) }, [])
  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const items = await api('/api/v1/transports')
        if (cancelled) return
        setTransports(items)
        if (!selected && items.length) {
          const requested = new URLSearchParams(window.location.search).get('transport')
          const requestedTransport = requested === 'latest'
            ? items.find(t => t.id.startsWith('PRESENTATION-'))
            : items.find(t => t.id === requested)
          setSelected(requestedTransport?.id || items.find(t => t.id === 'TRIP-DEMO-001')?.id || items[0].id)
        }
      } catch (e) { if (e.status === 401) onLogout(); else setError(e.message) }
    }
    load(); const id = setInterval(load, 10000)
    return () => { cancelled = true; clearInterval(id) }
  }, [selected])
  useEffect(() => {
    if (!selected) return
    let cancelled = false
    setSnapshot(null); setRows([]); setAlerts([]); setPage(0)
    async function load() {
      try {
        const [state, measures, events, health] = await Promise.all([
          api(`/api/v1/vehicles/VEH-001/state?transport_id=${selected}`),
          api(`/api/v1/transports/${selected}/measurements?limit=500`),
          api(`/api/v1/transports/${selected}/alerts`),
          api('/ready'),
        ])
        if (cancelled) return
        setSnapshot(state); setRows(measures.items); setTotal(measures.total)
        setAlerts(events); setServices(health); setError('')
      } catch (e) {
        if (cancelled) return
        if (e.status === 401) onLogout()
        else setError('La liaison avec le serveur est interrompue. Les dernières données restent affichées.')
      }
    }
    load(); const id = setInterval(load, 2000)
    return () => { cancelled = true; clearInterval(id) }
  }, [selected])
  useEffect(() => {
    if (!selected || tab !== 'history') return
    let cancelled = false
    api(`/api/v1/transports/${selected}/measurements?limit=25&offset=${page * 25}`)
      .then(result => { if (!cancelled) setHistory(result.items) })
      .catch(e => { if (!cancelled) setActionError(e.message) })
    return () => { cancelled = true }
  }, [selected, tab, page, total])

  const state = snapshot?.state
  const transport = transports.find(t => t.id === selected)
  const age = state?.measured_at ? Math.max(0, (tick - new Date(state.measured_at).getTime()) / 1000) : null
  const fresh = !error && age !== null && age <= 15
  const status = state?.thermal_status || 'empty'
  const position = state ? [state.latitude, state.longitude] : null
  const path = [...rows].reverse().filter(m => m.latitude != null).map(m => [m.latitude, m.longitude])
  const activeCount = alerts.filter(a => a.status === 'active').length
  const validRows = rows.filter(m => m.temperature_c != null)
  const normalRows = validRows.filter(m => m.temperature_c >= 2 && m.temperature_c <= 8)
  const inRange = validRows.length ? Math.round(normalRows.length / validRows.length * 100) : null
  const filteredAlerts = filter === 'all' ? alerts : alerts.filter(a => a.status === filter)
  const title = { overview: 'Vue d’ensemble', alerts: 'Historique des alertes', history: 'Journal des mesures' }[tab]

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><Snowflake size={29} /><span>froid<span className="brand-light">connect</span></span></div>
      <div className="workspace-label">ESPACE DE SUPERVISION</div>
      <nav aria-label="Navigation principale">
        {[['overview', LayoutDashboard, 'Vue d’ensemble'], ['alerts', Bell, 'Alertes'], ['history', Activity, 'Mesures']].map(([id, Icon, text]) =>
          <button key={id} className={`nav-item ${tab === id ? 'active' : ''}`} onClick={() => setTab(id)}><Icon size={19} />{text}{id === 'alerts' && activeCount > 0 && <b className="nav-count">{activeCount}</b>}</button>)}
      </nav>
      <div className="sidebar-note"><span className={`status-dot ${fresh ? '' : 'gray'}`} /><div><strong>Un véhicule suivi</strong><span>Prototype de transport simulé</span></div></div>
      <div className="sidebar-bottom"><div className="avatar">AA</div><div><strong>Achraf Abdelhedi</strong><span>Projet Internet des objets</span></div></div>
    </aside>
    <div className="main-shell">
      <header className="topbar"><div className="breadcrumb">Supervision<ChevronRight size={14} /><strong>{title}</strong></div>
        <div className="topbar-right"><span className="demo-badge">ENVIRONNEMENT SIMULÉ</span><button className="icon-button" aria-label="Se déconnecter" onClick={async () => { await api('/api/v1/auth/logout', { method: 'POST' }).catch(() => {}); onLogout() }}><LogOut size={18} /></button></div>
      </header>
      <main>
        <div className="page-heading"><div><div className="eyebrow">TRANSPORT SOUS TEMPÉRATURE CONTRÔLÉE</div><h1>{title}</h1><p>Gardez le bon degré, à chaque étape du trajet.</p></div><button className="button primary" onClick={() => setNewTransport(true)}><Plus size={17} />Nouveau transport</button></div>
        <section className="transport-bar" aria-label="Transport sélectionné">
          <span className="truck-icon"><Truck size={23} /></span>
          <div className="transport-select"><label htmlFor="transport">TRANSPORT SUIVI</label><select id="transport" value={selected} onChange={e => setSelected(e.target.value)}>{transports.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}</select></div>
          <span className="vehicle-code">VEH-001</span><span className={`pill ${transport?.status === 'completed' ? 'muted' : 'blue'}`}>{transport?.status === 'completed' ? 'Terminé' : 'En cours'}</span>
          <div className="transport-route"><MapPin size={15} />{transport?.origin || 'Tunis'}<ArrowRight size={15} />{transport?.destination || 'La Marsa'}</div>
        </section>
        {state?.source === 'simulator' && <div className="notice simulation"><Activity size={18} />Démonstration · Température et trajet simulés, historique enregistré.</div>}
        {error && <div className="notice error" role="alert"><WifiOff size={18} />{error}</div>}
        {actionError && <div className="notice error" role="alert">{actionError}<button className="icon-button" onClick={() => setActionError('')} aria-label="Fermer l’erreur"><X size={15} /></button></div>}
        {state && !fresh && !error && <div className="notice warning"><Clock3 size={18} />{age === null ? 'L’horloge du capteur n’est pas synchronisée.' : 'Les données sont anciennes. Le dernier état connu est conservé.'}</div>}
        {tab === 'overview' && <>
          <section className="stats-grid">
            <article className="stat-card"><div className="stat-label">Température actuelle<span className="stat-icon teal"><Thermometer size={20} /></span></div><div className="stat-value">{temperature(state?.temperature_c)}<span>°C</span></div><div className={`stat-foot ${status === 'alert' ? 'danger-text' : ''}`}><span className={`status-dot ${status === 'alert' ? 'red' : status === 'pending' ? 'amber' : ''}`} />{labels[status] || 'En attente du capteur'}</div></article>
            <article className="stat-card"><div className="stat-label">Plage de référence<span className="stat-icon blue"><ShieldCheck size={20} /></span></div><div className="stat-value range-value">2 <span>à</span> 8<span>°C</span></div><div className="stat-foot">Alarme après 30 s de dépassement</div></article>
            <article className="stat-card"><div className="stat-label">Alertes du transport<span className="stat-icon amber"><Bell size={20} /></span></div><div className="stat-value">{alerts.length}<span className="small-unit">événement{alerts.length > 1 ? 's' : ''}</span></div><div className="stat-foot">{activeCount ? `${activeCount} alerte active` : 'Aucune alerte active'}{status === 'pending' && ` · ${Math.floor(state.excursion_seconds)} / 30 s`}</div></article>
            <article className="stat-card"><div className="stat-label">Dernière réception<span className="stat-icon violet">{fresh ? <Wifi size={20} /> : <WifiOff size={20} />}</span></div><div className="stat-value time-value">{age == null ? '—' : age < 60 ? `${Math.floor(age)} s` : `${Math.floor(age / 60)} min`}</div><div className="stat-foot"><span className={`status-dot ${fresh ? '' : 'gray'}`} />{fresh ? 'Mesure récente' : state ? 'Données anciennes' : 'Aucune mesure reçue'}</div></article>
          </section>
          <div className="visual-grid">
            <section className="panel chart-panel"><div className="panel-heading"><div><h2>Évolution de la température</h2><p>Les {Math.min(total, 500)} dernières mesures · °C</p></div><span className="legend"><i />Plage normale</span></div><TemperatureChart rows={rows} /><div className="chart-footer"><span><i className="line-key" />Température mesurée</span><span>{inRange == null ? '—' : `${inRange} %`} des mesures dans la plage</span></div></section>
            <section className="panel map-panel"><div className="panel-heading"><div><h2>Position du véhicule</h2><p><span className="status-dot small" />Trajet GPS simulé</p></div><Route size={20} /></div>
              <div className="map-wrap"><MapContainer center={[36.835, 10.24]} zoom={11} scrollWheelZoom={false} aria-label="Carte du trajet">
                <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" eventHandlers={{ tileerror: () => setTileError(true) }} />
                {path.length > 1 && <Polyline positions={path} color="#159b98" weight={4} />}
                {position && <><CircleMarker center={position} radius={16} pathOptions={{ color: '#159b98', fillOpacity: 0.12, weight: 1 }} /><CircleMarker center={position} radius={7} pathOptions={{ color: 'white', fillColor: '#0c9290', fillOpacity: 1, weight: 3 }}><Popup>VEH-001 · {temperature(state.temperature_c)} °C</Popup></CircleMarker></>}
                <FollowVehicle position={position} path={path} />
              </MapContainer>{!state && <div className="map-empty">Position en attente</div>}{tileError && <div className="map-error">Fond de carte indisponible · coordonnées conservées</div>}</div>
              <div className="map-footer"><MapPin size={16} /><span>{position ? `${position[0].toFixed(5)}, ${position[1].toFixed(5)}` : 'Aucune coordonnée reçue'}</span><span className="pill muted">VEH-001</span></div>
            </section>
          </div>
          <div className="bottom-grid">
            <section className="panel"><div className="panel-heading"><div><h2>Derniers événements</h2><p>Traçabilité des excursions thermiques</p></div><button className="text-button" onClick={() => setTab('alerts')}>Tout voir<ArrowRight size={15} /></button></div><AlertList alerts={alerts.slice(0, 3)} compact /></section>
            <section className="panel system-panel"><div className="panel-heading"><div><h2>État du suivi</h2><p>Acquisition et conservation</p></div><Radio size={20} /></div>
              <div className="system-row"><span><Wifi size={16} />Véhicule</span><span className={`pill ${fresh ? 'green' : 'muted'}`}>{fresh ? 'Connecté' : 'En attente'}</span></div>
              <div className="system-row"><span><Database size={16} />Historique MongoDB</span><span className={`pill ${services?.mongodb === 'connected' && !error ? 'green' : 'amber'}`}>{services?.mongodb === 'connected' && !error ? 'Disponible' : 'Indisponible'}</span></div>
              <div className="system-row"><span><Activity size={16} />Synchronisation Firebase</span><span className={`pill ${services?.firebase === 'connected' ? 'green' : 'amber'}`}>{services?.firebase === 'connected' ? 'À jour' : 'En attente'}</span></div>
              <div className="system-bottom"><span>{total} mesures conservées</span><span>{state?.gap_count || 0} rupture(s) de continuité</span></div>
            </section>
          </div>
        </>}
        {tab === 'alerts' && <section className="panel full-panel"><div className="panel-heading"><div><h2>Événements thermiques</h2><p>Une excursion prolongée correspond à un événement.</p></div><select aria-label="Filtrer les alertes" value={filter} onChange={e => setFilter(e.target.value)}><option value="all">Tous les états</option><option value="active">Actives</option><option value="resolved">Résolues</option><option value="interrupted">Suivi interrompu</option></select></div><AlertList alerts={filteredAlerts} /></section>}
        {tab === 'history' && <section className="panel full-panel"><div className="panel-heading"><div><h2>Mesures enregistrées</h2><p>{total} mesures · Horaires affichés dans votre fuseau local</p></div><a className="button secondary" href={`/api/v1/transports/${selected}/export.csv`}><ArrowDownToLine size={16} />Exporter CSV</a></div>
          <div className="table-scroll"><table><thead><tr><th>Date de mesure</th><th>Température</th><th>Position</th><th>Capteur</th><th>Séquence</th><th>Source</th></tr></thead><tbody>{history.map(m => <tr key={`${m.boot_id}-${m.sequence}`}><td>{m.measured_at ? new Date(m.measured_at).toLocaleString('fr-FR') : 'Horloge non synchronisée'}</td><td><strong className={m.temperature_c != null && (m.temperature_c < 2 || m.temperature_c > 8) ? 'danger-text' : ''}>{temperature(m.temperature_c)} °C</strong></td><td>{m.latitude.toFixed(4)}, {m.longitude.toFixed(4)}</td><td><span className={`pill ${m.sensor_status === 'ok' ? 'green' : 'red'}`}>{m.sensor_status === 'ok' ? 'Valide' : 'Erreur'}</span></td><td>#{m.sequence}</td><td>{m.source === 'wokwi' ? 'Wokwi' : 'Simulateur Python'}</td></tr>)}</tbody></table></div>
          {!history.length && <div className="empty"><Activity /><strong>Aucune mesure enregistrée</strong></div>}
          <div className="pagination"><button className="button secondary" disabled={page === 0} onClick={() => setPage(page - 1)}>Précédent</button><span>Page {page + 1} / {Math.max(1, Math.ceil(total / 25))}</span><button className="button secondary" disabled={(page + 1) * 25 >= total} onClick={() => setPage(page + 1)}>Suivant</button></div>
        </section>}
        <footer className="page-footer"><span><Snowflake size={14} />Froid Connect · {realtime ? 'Temps réel Firebase' : 'Suivi par API'}</span><span>Seuils fictifs de démonstration · Source : {state?.source === 'simulator' ? 'simulateur Python' : state ? 'Wokwi' : 'en attente'}</span></footer>
      </main>
    </div>
    {newTransport && <NewTransport onClose={() => setNewTransport(false)} onCreated={item => { setTransports([item, ...transports]); setSelected(item.id); setNewTransport(false) }} />}
  </div>
}

function AlertList({ alerts, compact = false }) {
  if (!alerts.length) return <div className="empty events-empty"><span className="success-circle"><Check size={22} /></span><strong>Aucune alerte enregistrée</strong><span>Les dépassements prolongés apparaîtront ici.</span></div>
  return <div className="event-list">{alerts.map(a => <article className="event" key={a.id}><span className={`event-icon ${a.status === 'active' ? 'danger' : ''}`}><Thermometer size={19} /></span><div className="event-content"><strong>{a.direction === 'high' ? 'Dépassement du seuil haut' : 'Dépassement du seuil bas'}</strong><p>{date(a.started_at)}{a.ended_at ? ` → ${date(a.ended_at)}` : ''} · {Math.round(a.duration_seconds)} s · {temperature(a.direction === 'high' ? a.max_c : a.min_c)} °C</p>{!compact && <small>Déclenchement à {date(a.triggered_at)}</small>}</div><span className={`pill ${a.status === 'active' ? 'red' : a.status === 'resolved' ? 'green' : 'amber'}`}>{a.status === 'active' ? 'Active' : a.status === 'resolved' ? 'Résolue' : 'Suivi interrompu'}</span></article>)}</div>
}

function App() {
  const [authenticated, setAuthenticated] = useState(null)
  useEffect(() => { api('/api/v1/auth/session').then(() => setAuthenticated(true)).catch(() => setAuthenticated(false)) }, [])
  if (authenticated === null) return <div className="loading"><Snowflake size={34} /><span>Ouverture de la supervision…</span></div>
  return authenticated ? <Dashboard onLogout={() => setAuthenticated(false)} /> : <Login onLogin={() => setAuthenticated(true)} />
}

createRoot(document.getElementById('root')).render(<App />)
