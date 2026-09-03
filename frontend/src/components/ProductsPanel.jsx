import React, { useState, useEffect } from 'react'
import { Package, ChevronDown, ChevronRight, Check, X, Minus, AlertCircle } from 'lucide-react'
import api from '../services/api'

const STATUS_COLORS = {
  CONFORME: { bg: '#f0fff4', border: '#9ae6b4', text: '#276749', dot: '#38a169' },
  PARTIEL: { bg: '#fffbeb', border: '#fcd34d', text: '#92400e', dot: '#d97706' },
  NON_CONFORME: { bg: '#fff5f5', border: '#fc8181', text: '#c53030', dot: '#e53e3e' },
  NON_VERIFIE: { bg: '#f7fafc', border: '#cbd5e0', text: '#718096', dot: '#a0aec0' },
}

const s = {
  grid: { display: 'grid', gap: 16 },
  card: (selected) => ({
    background: '#fff', borderRadius: 12,
    border: `2px solid ${selected ? '#2b6cb0' : '#e2e8f0'}`,
    overflow: 'hidden', cursor: 'pointer',
    transition: 'box-shadow .2s',
    boxShadow: selected ? '0 0 0 3px rgba(43,108,176,.15)' : 'none',
  }),
  cardHead: {
    padding: '16px 20px',
    display: 'flex', alignItems: 'center', gap: 12,
    borderBottom: '1px solid #f0f0f0',
  },
  score: (v) => ({
    width: 52, height: 52, borderRadius: '50%', flexShrink: 0,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontSize: 14, fontWeight: 800,
    background: v >= 0.9 ? '#c6f6d5' : v >= 0.7 ? '#fefcbf' : '#fed7d7',
    color: v >= 0.9 ? '#22543d' : v >= 0.7 ? '#744210' : '#822727',
  }),
  prodName: { fontSize: 15, fontWeight: 700, color: '#1a202c' },
  prodRef: { fontSize: 13, color: '#718096', marginTop: 2 },
  mfr: { fontSize: 12, color: '#a0aec0' },
  strengths: { padding: '10px 20px', background: '#f0fff4', fontSize: 13 },
  gaps: { padding: '10px 20px', background: '#fff5f5', fontSize: 13 },
  listItem: { padding: '2px 0', display: 'flex', alignItems: 'flex-start', gap: 6 },
  detailBtn: {
    padding: '8px 20px', fontSize: 13, color: '#4a5568',
    borderTop: '1px solid #f0f0f0',
    display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer',
    background: 'none', border: 'none', width: '100%',
  },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 12 },
  th: {
    padding: '8px 10px', background: '#2b6cb0', color: '#fff',
    fontWeight: 600, textAlign: 'left',
  },
  td: { padding: '6px 10px', borderBottom: '1px solid #f0f0f0' },
  statusBadge: (st) => ({
    padding: '2px 8px', borderRadius: 99, fontSize: 11, fontWeight: 600,
    background: STATUS_COLORS[st]?.bg || '#f7fafc',
    color: STATUS_COLORS[st]?.text || '#718096',
    border: `1px solid ${STATUS_COLORS[st]?.border || '#cbd5e0'}`,
  }),
  selectedCheck: {
    marginLeft: 'auto', width: 24, height: 24, borderRadius: '50%',
    background: '#2b6cb0', display: 'flex', alignItems: 'center', justifyContent: 'center',
  },
  generateBtn: {
    marginTop: 20, padding: '14px', width: '100%', borderRadius: 10,
    background: 'linear-gradient(135deg, #1a365d, #2b6cb0)',
    color: '#fff', border: 'none', fontSize: 15, fontWeight: 700,
    cursor: 'pointer',
  },
  loading: {
    textAlign: 'center', padding: '40px 20px', color: '#718096',
    fontSize: 14,
  },
  empty: {
    textAlign: 'center', padding: '40px 20px', color: '#718096',
    fontSize: 14,
  },
  error: {
    textAlign: 'center', padding: '20px', color: '#e53e3e',
    fontSize: 14, background: '#fff5f5', borderRadius: 8,
    border: '1px solid #fc8181',
  },
  incompatibilities: {
    padding: '10px 20px',
    background: '#fff5f5',
    borderTop: '1px solid #fc8181',
    fontSize: 13,
  },
  incompatTitle: {
    fontWeight: 700,
    color: '#c53030',
    fontSize: 13,
    marginBottom: 4,
  },
  incompatItem: {
    padding: '2px 0',
    fontSize: 12,
    color: '#c53030',
    display: 'flex',
    alignItems: 'flex-start',
    gap: 6,
  },
  alternatives: {
    padding: '10px 20px',
    background: '#ebf8ff',
    borderTop: '1px solid #90cdf4',
    fontSize: 13,
  },
  altTitle: {
    fontWeight: 700,
    color: '#2b6cb0',
    fontSize: 13,
    marginBottom: 4,
  },
  altItem: {
    padding: '2px 0',
    fontSize: 12,
    color: '#2b6cb0',
    display: 'flex',
    alignItems: 'flex-start',
    gap: 6,
  },
}

function StatusIcon({ status }) {
  if (status === 'CONFORME') return <Check size={14} color="#38a169" />
  if (status === 'NON_CONFORME') return <X size={14} color="#e53e3e" />
  return <Minus size={14} color="#d97706" />
}

function ProductCard({ product, selected, onToggle }) {
  const [showDetail, setShowDetail] = useState(false)
  const pct = Math.round(product.compliance_score * 100)

  const criticalIncompatibilities = product.incompatibilities?.filter(
    inc => inc.severity === 'critique'
  ) || []

  return (
    <div style={s.card(selected)} onClick={onToggle}>
      <div style={s.cardHead}>
        <div style={s.score(product.compliance_score)}>{pct}%</div>
        <div style={{ flex: 1 }}>
          <div style={s.prodName}>{product.product_name}</div>
          <div style={s.prodRef}>{product.manufacturer} — <strong>{product.reference}</strong></div>
        </div>
        {selected && (
          <div style={s.selectedCheck}>
            <Check size={14} color="#fff" />
          </div>
        )}
      </div>

      {criticalIncompatibilities.length > 0 && (
        <div style={s.incompatibilities}>
          <div style={s.incompatTitle}>🚨 Incompatibilités critiques ({criticalIncompatibilities.length})</div>
          {criticalIncompatibilities.slice(0, 3).map((inc, i) => (
            <div key={i} style={s.incompatItem}>
              <span>•</span>
              <span>
                <strong>{inc.requirement_id}</strong>: {inc.requirement_text}
                <span style={{ display: 'block', fontSize: 11, color: '#9b2c2c' }}>
                  {inc.reason || 'Le produit ne répond pas à cette exigence'}
                </span>
              </span>
            </div>
          ))}
        </div>
      )}

      {product.alternatives?.length > 0 && (
        <div style={s.alternatives}>
          <div style={s.altTitle}>💡 Alternatives suggérées</div>
          {product.alternatives.slice(0, 3).map((alt, i) => (
            <div key={i} style={s.altItem}>
              <span>•</span>
              <span>
                <strong>{alt.product_name}</strong> ({alt.manufacturer})
                {alt.compliance_score && (
                  <span style={{ marginLeft: 8, color: '#2f855a' }}>
                    Score: {Math.round(alt.compliance_score * 100)}%
                  </span>
                )}
                <span style={{ display: 'block', fontSize: 11, color: '#2b6cb0' }}>
                  {alt.why || 'Alternative recommandée'}
                </span>
              </span>
            </div>
          ))}
        </div>
      )}

      {product.strengths?.length > 0 && (
        <div style={s.strengths}>
          {product.strengths.slice(0, 2).map((s_, i) => (
            <div key={i} style={s.listItem}>
              <Check size={13} color="#38a169" style={{ flexShrink: 0, marginTop: 1 }} />
              {s_}
            </div>
          ))}
        </div>
      )}

      {product.gaps?.length > 0 && (
        <div style={s.gaps}>
          {product.gaps.slice(0, 2).map((g, i) => (
            <div key={i} style={s.listItem}>
              <X size={13} color="#e53e3e" style={{ flexShrink: 0, marginTop: 1 }} />
              {g}
            </div>
          ))}
        </div>
      )}

      <button style={s.detailBtn}
        onClick={e => { e.stopPropagation(); setShowDetail(v => !v) }}>
        {showDetail ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        Voir le tableau de conformité ({product.compliance_rows?.length || 0} critères)
      </button>

      {showDetail && product.compliance_rows?.length > 0 && (
        <div style={{ overflowX: 'auto', padding: '0 20px 16px' }} onClick={e => e.stopPropagation()}>
          <table style={s.table}>
            <thead>
              <tr>
                <th style={s.th}>ID</th>
                <th style={s.th}>Exigence</th>
                <th style={s.th}>Réponse Produit</th>
                <th style={s.th}>Statut</th>
              </tr>
            </thead>
            <tbody>
              {product.compliance_rows.map((row, i) => (
                <tr key={row.requirement_id + i} style={{ background: i % 2 === 0 ? '#fff' : '#f7fafc' }}>
                  <td style={s.td}>{row.requirement_id}</td>
                  <td style={s.td}>{row.requirement_text}</td>
                  <td style={s.td}>{row.product_response}</td>
                  <td style={s.td}>
                    <span style={s.statusBadge(row.status)}>
                      <StatusIcon status={row.status} /> {row.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default function ProductsPanel({ 
  sessionId, 
  requirements, 
  products: backendProducts = [],  // ✅ PROP RENOMMÉE
  onGenerate, 
  generating 
}) {
  // ✅ PLUS DE CONFLIT DE NOMS
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [selected, setSelected] = useState([])

  // ✅ UTILISER DIRECTEMENT LES PRODUITS DU BACKEND
  const matchedProducts = backendProducts

  console.log('📥 Produits reçus du backend:', backendProducts)

  function toggle(id) {
    setSelected(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    )
  }

  const handleGenerate = () => {
    if (selected.length === 0) {
      alert('Veuillez sélectionner au moins un produit');
      return
    }
    onGenerate(selected)
  }

  // ✅ AFFICHAGE DU CHARGEMENT (si les produits ne sont pas encore là)
  if (!backendProducts || backendProducts.length === 0) {
    return (
      <div>
        <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 10 }}>
          <Package size={20} color="#2b6cb0" />
          <span style={{ fontWeight: 700, fontSize: 16 }}>Aucun produit recommandé</span>
        </div>
        <div style={s.empty}>
          <div>📦 Aucun produit n'a été recommandé pour ce cahier des charges.</div>
          <div style={{ fontSize: 12, marginTop: 8 }}>
            Vérifiez que le catalogue contient des produits et que le matching a bien fonctionné.
          </div>
        </div>
      </div>
    )
  }

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 10 }}>
        <Package size={20} color="#2b6cb0" />
        <span style={{ fontWeight: 700, fontSize: 16 }}>
          Produits Recommandés ({matchedProducts.length})
        </span>
        <span style={{ fontSize: 13, color: '#718096', marginLeft: 'auto' }}>
          Sélectionnez les produits à inclure dans l'offre
        </span>
      </div>

      <div style={s.grid}>
        {matchedProducts.map((p, index) => (
          <ProductCard
            key={p.product_id || index}
            product={p}
            selected={selected.includes(p.product_id)}
            onToggle={() => toggle(p.product_id)}
          />
        ))}
      </div>

      <button
        style={{
          ...s.generateBtn,
          opacity: selected.length === 0 ? 0.6 : 1,
          cursor: selected.length === 0 ? 'not-allowed' : 'pointer'
        }}
        onClick={handleGenerate}
        disabled={generating || selected.length === 0}
      >
        {generating
          ? '⏳ Génération de l\'offre en cours…'
          : selected.length === 0
          ? 'Sélectionnez au moins un produit'
          : `🚀 Générer l'offre technique (${selected.length} produit${selected.length > 1 ? 's' : ''})`
        }
      </button>
    </div>
  )
}