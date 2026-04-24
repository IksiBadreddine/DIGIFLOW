import React, { useState } from 'react'
import { ChevronDown, ChevronRight, CheckCircle } from 'lucide-react'

const s = {
  card: {
    background: '#fff', borderRadius: 12, border: '1px solid #e2e8f0',
    overflow: 'hidden', marginBottom: 24,
  },
  header: {
    background: 'linear-gradient(135deg, #1a365d, #2b6cb0)',
    padding: '16px 20px', color: '#fff',
    display: 'flex', alignItems: 'center', gap: 10,
  },
  title: { fontSize: 16, fontWeight: 700 },
  badge: {
    background: 'rgba(255,255,255,.2)', borderRadius: 99,
    padding: '2px 10px', fontSize: 12,
  },
  summary: {
    padding: '16px 20px', background: '#ebf8ff',
    borderBottom: '1px solid #bee3f8',
    fontSize: 14, color: '#2d3748', lineHeight: 1.6,
  },
  constraints: {
    padding: '12px 20px', background: '#fffbeb',
    borderBottom: '1px solid #fef08a',
  },
  constraintTitle: { fontSize: 13, fontWeight: 700, color: '#92400e', marginBottom: 8 },
  constraintItem: {
    fontSize: 13, color: '#78350f', padding: '3px 0',
    display: 'flex', alignItems: 'flex-start', gap: 6,
  },
  body: { padding: '16px 20px' },
  sectionHead: {
    display: 'flex', alignItems: 'center', gap: 8,
    cursor: 'pointer', padding: '8px 0',
    borderBottom: '1px solid #f0f0f0',
    userSelect: 'none',
  },
  sectionLabel: { fontWeight: 600, fontSize: 14, color: '#2d3748', flex: 1 },
  reqItem: {
    padding: '8px 12px', marginTop: 4,
    background: '#f7fafc', borderRadius: 6,
    borderLeft: '3px solid #90cdf4',
    fontSize: 13, color: '#4a5568',
  },
  reqId: { fontWeight: 700, color: '#2b6cb0', marginRight: 8 },
  reqVal: { color: '#718096', marginLeft: 4, fontStyle: 'italic' },
}

export default function RequirementsPanel({ analysis }) {
  const [openSections, setOpenSections] = useState({})

  if (!analysis) return null

  // Group requirements by section
  const groups = {}
  for (const r of (analysis.extracted_requirements || [])) {
    if (!groups[r.section]) groups[r.section] = []
    groups[r.section].push(r)
  }

  function toggle(sec) {
    setOpenSections(prev => ({ ...prev, [sec]: !prev[sec] }))
  }

  return (
    <div style={s.card}>
      <div style={s.header}>
        <CheckCircle size={20} />
        <span style={s.title}>Exigences Extraites</span>
        <span style={s.badge}>{analysis.extracted_requirements?.length || 0} exigences</span>
      </div>

      {analysis.summary && (
        <div style={s.summary}>
          <strong>Synthèse : </strong>{analysis.summary}
        </div>
      )}

      {analysis.key_constraints?.length > 0 && (
        <div style={s.constraints}>
          <div style={s.constraintTitle}>⚠ Contraintes Clés</div>
          {analysis.key_constraints.map((c, i) => (
            <div key={i} style={s.constraintItem}>
              <span>•</span> {c}
            </div>
          ))}
        </div>
      )}

      <div style={s.body}>
        {Object.entries(groups).map(([section, reqs]) => (
          <div key={section}>
            <div style={s.sectionHead} onClick={() => toggle(section)}>
              {openSections[section]
                ? <ChevronDown size={16} color="#718096" />
                : <ChevronRight size={16} color="#718096" />}
              <span style={s.sectionLabel}>{section}</span>
              <span style={{ fontSize: 12, color: '#a0aec0' }}>{reqs.length}</span>
            </div>
            {openSections[section] && reqs.map(r => (
              <div key={r.id} style={s.reqItem}>
                <span style={s.reqId}>{r.id}</span>
                {r.description}
                {r.value && <span style={s.reqVal}>→ {r.value}</span>}
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}
