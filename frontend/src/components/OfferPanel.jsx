import React, { useState } from 'react'
import { FileDown, BookOpen, List, ChevronDown, ChevronRight, Check, X, Minus } from 'lucide-react'
import { exportDocxUrl } from '../services/api.js'

const STATUS_COLORS = {
  CONFORME: { bg: '#f0fff4', text: '#276749' },
  PARTIEL: { bg: '#fffbeb', text: '#92400e' },
  NON_CONFORME: { bg: '#fff5f5', text: '#c53030' },
  NON_VERIFIE: { bg: '#f7fafc', text: '#718096' },
}

const s = {
  banner: {
    background: 'linear-gradient(135deg, #1a365d, #2b6cb0)',
    borderRadius: 12, padding: '24px 28px', color: '#fff', marginBottom: 20,
    display: 'flex', alignItems: 'center', gap: 20,
  },
  offerTitle: { fontSize: 20, fontWeight: 800, marginBottom: 4 },
  offerRef: { fontSize: 14, opacity: .8 },
  scoreCircle: {
    width: 72, height: 72, borderRadius: '50%',
    background: 'rgba(255,255,255,.15)',
    display: 'flex', flexDirection: 'column',
    alignItems: 'center', justifyContent: 'center',
    flexShrink: 0,
  },
  scoreNum: { fontSize: 22, fontWeight: 800 },
  scoreLabel: { fontSize: 10, opacity: .8 },
  exportBtn: {
    marginLeft: 'auto',
    padding: '10px 20px', borderRadius: 8,
    background: 'rgba(255,255,255,.2)', color: '#fff',
    border: '1px solid rgba(255,255,255,.4)',
    fontSize: 14, fontWeight: 600, cursor: 'pointer',
    display: 'flex', alignItems: 'center', gap: 6,
  },
  tabs: {
    display: 'flex', gap: 4, marginBottom: 20,
    borderBottom: '2px solid #e2e8f0',
  },
  tab: (active) => ({
    padding: '10px 20px', border: 'none', background: 'none', cursor: 'pointer',
    fontSize: 14, fontWeight: active ? 700 : 400,
    color: active ? '#2b6cb0' : '#718096',
    borderBottom: active ? '2px solid #2b6cb0' : '2px solid transparent',
    marginBottom: -2,
  }),
  section: {
    background: '#fff', borderRadius: 10, border: '1px solid #e2e8f0',
    marginBottom: 12, overflow: 'hidden',
  },
  secHead: {
    padding: '14px 20px', fontWeight: 700, fontSize: 15, color: '#1a365d',
    display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer',
    background: '#f8fafc',
  },
  secBody: { padding: '16px 20px', fontSize: 14, lineHeight: 1.8, color: '#2d3748' },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 13 },
  th: { padding: '10px 12px', background: '#2b6cb0', color: '#fff', fontWeight: 600, textAlign: 'left' },
  td: { padding: '8px 12px', borderBottom: '1px solid #f0f0f0' },
  badge: (st) => ({
    padding: '3px 8px', borderRadius: 99, fontSize: 11, fontWeight: 700,
    background: STATUS_COLORS[st]?.bg, color: STATUS_COLORS[st]?.text,
  }),
}

function SectionCard({ section }) {
  const [open, setOpen] = useState(true)
  return (
    <div style={s.section}>
      <div style={s.secHead} onClick={() => setOpen(v => !v)}>
        {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        {section.title}
      </div>
      {open && (
        <div style={s.secBody}>
          {section.content.split('\n').map((line, i) => (
            <p key={i} style={{ marginBottom: 6 }}>{line}</p>
          ))}
        </div>
      )}
    </div>
  )
}

export default function OfferPanel({ offer, sessionId }) {
  const [tab, setTab] = useState('sections')
  if (!offer) return null

  const conformes = (offer.compliance_table || []).filter(r => r.status === 'CONFORME').length
  const total = offer.compliance_table?.length || 0
  const pct = Math.round(offer.total_compliance_rate * 100)

  return (
    <div>
      <div style={s.banner}>
        <div style={s.scoreCircle}>
          <span style={s.scoreNum}>{pct}%</span>
          <span style={s.scoreLabel}>CONFORMITÉ</span>
        </div>
        <div style={{ flex: 1 }}>
          <div style={s.offerTitle}>{offer.title}</div>
          <div style={s.offerRef}>{offer.reference} — {conformes}/{total} exigences conformes</div>
        </div>
        <a href={exportDocxUrl(sessionId)} download>
          <button style={s.exportBtn}>
            <FileDown size={16} /> Exporter DOCX
          </button>
        </a>
      </div>

      <div style={s.tabs}>
        {[
          { key: 'sections', label: '📄 Offre Technique', icon: BookOpen },
          { key: 'boq', label: '📦 BOQ' },
          { key: 'compliance', label: '✅ Tableau Conformité' },
        ].map(t => (
          <button key={t.key} style={s.tab(tab === t.key)} onClick={() => setTab(t.key)}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'sections' && (
        <div>
          {(offer.sections || []).map((sec, i) => (
            <SectionCard key={i} section={sec} />
          ))}
        </div>
      )}

      {tab === 'boq' && (
        <div style={{ background: '#fff', borderRadius: 10, border: '1px solid #e2e8f0', overflow: 'auto' }}>
          <table style={s.table}>
            <thead>
              <tr>
                {['Pos.', 'Désignation', 'Référence', 'Fabricant', 'Unité', 'Qté', 'Remarques'].map(h => (
                  <th key={h} style={s.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(offer.boq || []).map((item, i) => (
                <tr key={i} style={{ background: i % 2 === 0 ? '#fff' : '#f7fafc' }}>
                  <td style={s.td}>{item.pos}</td>
                  <td style={s.td}>{item.designation}</td>
                  <td style={{ ...s.td, fontWeight: 600, color: '#2b6cb0' }}>{item.reference}</td>
                  <td style={s.td}>{item.manufacturer}</td>
                  <td style={s.td}>{item.unit}</td>
                  <td style={{ ...s.td, textAlign: 'center', fontWeight: 700 }}>{item.quantity}</td>
                  <td style={{ ...s.td, color: '#718096', fontSize: 12 }}>{item.remarks}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'compliance' && (
        <div style={{ background: '#fff', borderRadius: 10, border: '1px solid #e2e8f0', overflow: 'auto' }}>
          <table style={s.table}>
            <thead>
              <tr>
                {['ID', 'Exigence', 'Valeur Requise', 'Réponse Produit', 'Statut', 'Remarques'].map(h => (
                  <th key={h} style={s.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(offer.compliance_table || []).map((row, i) => (
                <tr key={i} style={{ background: i % 2 === 0 ? '#fff' : '#f7fafc' }}>
                  <td style={{ ...s.td, fontWeight: 600, color: '#2b6cb0', whiteSpace: 'nowrap' }}>{row.requirement_id}</td>
                  <td style={s.td}>{row.requirement_text}</td>
                  <td style={{ ...s.td, color: '#718096' }}>{row.specified_value}</td>
                  <td style={s.td}>{row.product_response}</td>
                  <td style={{ ...s.td, whiteSpace: 'nowrap' }}>
                    <span style={s.badge(row.status)}>{row.status}</span>
                  </td>
                  <td style={{ ...s.td, color: '#718096', fontSize: 12 }}>{row.remarks}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
