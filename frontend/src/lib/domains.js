// Domain colors + classification. The backend doesn't return a "domain" field,
// so we classify client-side from the query/answer text for the colored dots and
// the topic chips described in the design handoff (Design Tokens → Colors).

export const DOMAINS = {
  combustion: { label: 'Combustion', color: '#3358e0' },
  fuel: { label: 'Fuel', color: '#1f9bd1' },
  ignition: { label: 'Ignition', color: '#d98a1f' },
  cooling: { label: 'Cooling', color: '#18a08a' },
  oil: { label: 'Lubrication', color: '#6b7384' },
}

// The 8 landing-page topic chips (design handoff §3).
export const TOPIC_CHIPS = [
  { label: 'Expansion Chamber', domain: 'combustion' },
  { label: 'Carburetor', domain: 'fuel' },
  { label: 'Ignition Timing', domain: 'ignition' },
  { label: 'Port Timing', domain: 'combustion' },
  { label: 'Premix & Lubrication', domain: 'oil' },
  { label: 'Cooling', domain: 'cooling' },
  { label: 'Detonation', domain: 'ignition' },
  { label: 'Reed Valve', domain: 'fuel' },
]

const KEYWORDS = {
  fuel: ['fuel', 'jet', 'carburet', 'carb', 'mixture', 'octane', 'gasoline', 'petrol', 'needle', 'float'],
  ignition: ['ignition', 'timing', 'spark', 'plug', 'detonation', 'knock', 'advance', 'cdi', 'coil'],
  cooling: ['cool', 'temperature', 'overheat', 'fan', 'water', 'radiator', 'thermal'],
  oil: ['oil', 'lubric', 'premix', 'grease', 'ratio'],
  combustion: ['port', 'chamber', 'squish', 'compression', 'piston', 'cylinder', 'exhaust', 'transfer', 'crankcase', 'reed'],
}

// Best-effort domain guess from free text → a key in DOMAINS.
export function classifyDomain(text = '') {
  const t = text.toLowerCase()
  let best = 'combustion'
  let bestScore = 0
  for (const [domain, words] of Object.entries(KEYWORDS)) {
    const score = words.reduce((n, w) => n + (t.includes(w) ? 1 : 0), 0)
    if (score > bestScore) {
      bestScore = score
      best = domain
    }
  }
  return best
}

export const domainColor = (key) => (DOMAINS[key] || DOMAINS.combustion).color
export const domainLabel = (key) => (DOMAINS[key] || DOMAINS.combustion).label
