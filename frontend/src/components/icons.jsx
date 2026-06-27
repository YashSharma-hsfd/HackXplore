// Small inline SVG icons used across the UI (keeps the bundle dependency-free).

export function HirthBadge() {
  // White H-shape inside the blue badge, skewed -8deg (design handoff §2).
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
      <g transform="skewX(-8)" fill="#fff">
        <rect x="3" y="3" width="3.2" height="16" rx="1" />
        <rect x="13" y="3" width="3.2" height="16" rx="1" />
        <rect x="3" y="9.4" width="13.2" height="3.2" rx="1" />
      </g>
    </svg>
  )
}

export function GlobeIcon({ size = 17, color = 'currentColor' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.6">
      <circle cx="12" cy="12" r="9" />
      <ellipse cx="12" cy="12" rx="4" ry="9" />
      <line x1="3" y1="12" x2="21" y2="12" />
      <path d="M5 7c2 1.4 12 1.4 14 0M5 17c2-1.4 12-1.4 14 0" />
    </svg>
  )
}

export function PencilIcon({ size = 13 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" />
    </svg>
  )
}

export function UploadCloud({ size = 28 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M16 16l-4-4-4 4" />
      <path d="M12 12v9" />
      <path d="M20.4 16.6A5 5 0 0 0 18 7h-1.3A8 8 0 1 0 3 14.9" />
    </svg>
  )
}
