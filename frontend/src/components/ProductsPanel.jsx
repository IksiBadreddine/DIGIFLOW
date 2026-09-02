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

  // ✅ Compter les incompatibilités critiques
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

      {/* ✅ AFFICHER LES INCOMPATIBILITÉS CRITIQUES */}
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

      {/* ✅ AFFICHER LES ALTERNATIVES */}
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

      {/* POINTS FORTS */}
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

      {/* ÉCARTS */}
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

      {/* BOUTON TABLEAU DE CONFORMITÉ */}
      <button style={s.detailBtn}
        onClick={e => { e.stopPropagation(); setShowDetail(v => !v) }}>
        {showDetail ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        Voir le tableau de conformité ({product.compliance_rows?.length || 0} critères)
      </button>

      {/* TABLEAU DE CONFORMITÉ */}
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
                <tr key={i} style={{ background: i % 2 === 0 ? '#fff' : '#f7fafc' }}>
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

export default function ProductsPanel({ sessionId, requirements, onGenerate, generating }) {
  const [catalogProducts, setCatalogProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selected, setSelected] = useState([])

  useEffect(() => {
    loadCatalog()
  }, [])

  const loadCatalog = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const response = await api.get('/products')
      
      // Extraire les produits de la réponse
      const products = response.data?.products || response.data || []
      setCatalogProducts(products)
      
    } catch (err) {
      console.error('Erreur de chargement du catalogue:', err)
      setError('Impossible de charger le catalogue produits')
    } finally {
      setLoading(false)
    }
  }

  const handleGenerate = () => {
    if (selected.length === 0) {
      alert('Veuillez sélectionner au moins un produit');
      return;
    }
    
    // ✅ Appeler onGenerate directement, sans setGenerating
    // La gestion du chargement se fait dans App.jsx
    onGenerate(selected);
  };


  // Fonction de matching simple
  const getMatchedProducts = () => {
    if (!requirements || requirements.length === 0) {
      return catalogProducts.map(p => ({
        product_id: p.id,
        product_name: p.name,
        manufacturer: p.manufacturer,
        reference: p.reference,
        compliance_score: 0.5,
        compliance_rows: [],
        strengths: ['Produit disponible'],
        gaps: ['En attente d\'exigences']
      }))
    }

    return catalogProducts.map(product => {
      // Calculer un score basé sur les mots-clés
      let matchedCount = 0
      const reqTexts = requirements.map(r => (r.description || '').toLowerCase())
      const productText = [
        product.name || '',
        product.manufacturer || '',
        ...Object.values(product.specs || {}),
        ...(product.tags || [])
      ].join(' ').toLowerCase()

      reqTexts.forEach(req => {
        const words = req.split(' ')
        words.forEach(word => {
          if (word.length > 3 && productText.includes(word)) {
            matchedCount++
          }
        })
      })

      const maxMatches = Math.max(reqTexts.join(' ').split(' ').filter(w => w.length > 3).length, 1)
      const score = Math.min(matchedCount / maxMatches + 0.2, 1)

      // Générer des statuts aléatoires pour l'exemple
      const statuses = ['CONFORME', 'PARTIEL', 'NON_CONFORME', 'NON_VERIFIE']
      
      return {
        product_id: product.id,
        product_name: product.name,
        manufacturer: product.manufacturer,
        reference: product.reference,
        compliance_score: score,
        compliance_rows: requirements.slice(0, 8).map(req => ({
          requirement_id: req.id || 'REQ-001',
          requirement_text: (req.description || '').substring(0, 60),
          product_response: product.specs?.[Object.keys(product.specs)[0]] || 'Disponible',
          status: statuses[Math.floor(Math.random() * statuses.length)],
          remarks: 'À vérifier en détail'
        })),
        strengths: ['Compatibilité technique', 'Marque reconnue'],
        gaps: ['Vérification supplémentaire requise']
      }
    })
  }

  const matchedProducts = getMatchedProducts()

  function toggle(id) {
    setSelected(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    )
  }

  // Affichage en chargement
  if (loading) {
    return (
      <div>
        <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 10 }}>
          <Package size={20} color="#2b6cb0" />
          <span style={{ fontWeight: 700, fontSize: 16 }}>Chargement du catalogue...</span>
        </div>
        <div style={s.loading}>
          <div>⏳ Chargement des produits disponibles...</div>
        </div>
      </div>
    )
  }

  // Affichage d'erreur
  if (error) {
    return (
      <div>
        <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 10 }}>
          <Package size={20} color="#2b6cb0" />
          <span style={{ fontWeight: 700, fontSize: 16 }}>Erreur de chargement</span>
        </div>
        <div style={s.error}>
          <AlertCircle size={16} style={{ marginRight: 8 }} />
          {error}
        </div>
      </div>
    )
  }

  // Affichage si catalogue vide
  if (catalogProducts.length === 0) {
    return (
      <div>
        <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 10 }}>
          <Package size={20} color="#2b6cb0" />
          <span style={{ fontWeight: 700, fontSize: 16 }}>Aucun produit disponible</span>
        </div>
        <div style={s.empty}>
          <div>📦 Le catalogue produits est vide.</div>
          <div style={{ fontSize: 12, marginTop: 8 }}>
            Ajoutez des produits dans <code>data/products/catalog.json</code>
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
          {requirements && requirements.length > 0 
            ? `Sélectionnez les produits à inclure dans l'offre`
            : 'Téléchargez un CDC pour voir les recommandations'
          }
        </span>
      </div>

      {(!requirements || requirements.length === 0) && (
        <div style={s.empty}>
          📄 Téléchargez un cahier des charges pour générer des recommandations produits.
        </div>
      )}

      {requirements && requirements.length > 0 && matchedProducts.length === 0 && (
        <div style={s.empty}>
          🔍 Aucun produit ne correspond aux exigences.
        </div>
      )}

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

      {requirements && requirements.length > 0 && matchedProducts.length > 0 && (
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
      )}
    </div>
  )
}