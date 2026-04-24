import React, { useState } from 'react'
import UploadZone from './components/UploadZone.jsx'
import RequirementsPanel from './components/RequirementsPanel.jsx'
import ProductsPanel from './components/ProductsPanel.jsx'
import OfferPanel from './components/OfferPanel.jsx'
import { generateOffer } from './services/api.js'

// ── Styles ──────────────────────────────────────────────────────────────────
const s = {
  app: { minHeight: '100vh', background: '#f0f4f8' },

  // Navbar
  nav: {
    background: 'linear-gradient(135deg, #0f2347, #1a365d)',
    padding: '0 32px', height: 60,
    display: 'flex', alignItems: 'center', gap: 12,
    boxShadow: '0 2px 8px rgba(0,0,0,.3)',
  },
  navLogo: { fontSize: 20, fontWeight: 800, color: '#fff', letterSpacing: '-0.5px' },
  navSub: { fontSize: 13, color: '#90cdf4', marginLeft: 4 },
  navPill: {
    marginLeft: 'auto', padding: '4px 12px', borderRadius: 99,
    background: 'rgba(255,255,255,.1)', color: '#90cdf4', fontSize: 12,
  },

  // Stepper
  stepper: {
    background: '#fff', borderBottom: '1px solid #e2e8f0',
    padding: '0 32px',
    display: 'flex', alignItems: 'stretch',
  },
  step: (active, done) => ({
    display: 'flex', alignItems: 'center', gap: 10,
    padding: '14px 24px', cursor: done ? 'pointer' : 'default',
    borderBottom: active ? '3px solid #2b6cb0' : '3px solid transparent',
    opacity: !active && !done ? 0.45 : 1,
    transition: 'all .2s',
  }),
  stepNum: (active, done) => ({
    width: 26, height: 26, borderRadius: '50%', flexShrink: 0,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontSize: 12, fontWeight: 700,
    background: done ? '#38a169' : active ? '#2b6cb0' : '#cbd5e0',
    color: '#fff',
  }),
  stepLabel: (active) => ({
    fontSize: 13, fontWeight: active ? 700 : 500,
    color: active ? '#1a365d' : '#4a5568',
    whiteSpace: 'nowrap',
  }),
  stepSep: { width: 32, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#cbd5e0' },

  // Layout
  main: { maxWidth: 1100, margin: '0 auto', padding: '32px 24px' },
  cols: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 },

  // Cards
  card: {
    background: '#fff', borderRadius: 14,
    border: '1px solid #e2e8f0',
    padding: '24px 28px',
    boxShadow: '0 1px 4px rgba(0,0,0,.05)',
  },
  cardTitle: {
    fontSize: 16, fontWeight: 700, color: '#1a365d',
    marginBottom: 20, display: 'flex', alignItems: 'center', gap: 8,
  },

  // Alert
  alert: (type) => ({
    padding: '14px 18px', borderRadius: 10, marginBottom: 20,
    fontSize: 14, display: 'flex', alignItems: 'center', gap: 10,
    background: type === 'error' ? '#fff5f5' : '#ebf8ff',
    border: `1px solid ${type === 'error' ? '#fc8181' : '#90cdf4'}`,
    color: type === 'error' ? '#c53030' : '#2c5282',
  }),

  // Spinner overlay
  overlay: {
    position: 'fixed', inset: 0,
    background: 'rgba(15,35,71,.65)',
    display: 'flex', flexDirection: 'column',
    alignItems: 'center', justifyContent: 'center',
    zIndex: 999,
  },
  spinnerBox: {
    background: '#fff', borderRadius: 16, padding: '36px 48px',
    textAlign: 'center', boxShadow: '0 8px 32px rgba(0,0,0,.2)',
  },
  spinner: {
    width: 52, height: 52, border: '5px solid #e2e8f0',
    borderTop: '5px solid #2b6cb0',
    borderRadius: '50%', margin: '0 auto 16px',
    animation: 'spin 1s linear infinite',
  },
  spinText: { fontSize: 16, fontWeight: 700, color: '#1a365d', marginBottom: 6 },
  spinSub: { fontSize: 13, color: '#718096' },
}

const STEPS = [
  { id: 'upload',       label: 'Upload CdC',           emoji: '📄' },
  { id: 'requirements', label: 'Exigences extraites',  emoji: '🔍' },
  { id: 'products',     label: 'Produits recommandés', emoji: '📦' },
  { id: 'offer',        label: 'Offre générée',        emoji: '🚀' },
]

export default function App() {
  const [step, setStep]           = useState(0)   // 0-3
  const [sessionId, setSessionId] = useState(null)
  const [analysis, setAnalysis]   = useState(null)
  const [offer, setOffer]         = useState(null)
  const [loading, setLoading]     = useState(false)
  const [generating, setGenerating] = useState(false)
  const [error, setError]         = useState('')

  // ── Handlers ──────────────────────────────────────────────────────────────

  function handleAnalysis(result) {
    setSessionId(result.session_id)
    setAnalysis(result.analysis)
    setStep(1)
    setError('')
  }

  async function handleGenerate(selectedIds) {
    setGenerating(true)
    setError('')
    try {
      const data = await generateOffer(sessionId, selectedIds)
      setOffer(data)
      setStep(3)
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Erreur lors de la génération')
    } finally {
      setGenerating(false)
    }
  }

  function goToStep(idx) {
    if (idx < step) setStep(idx)
  }

  function reset() {
    setStep(0); setSessionId(null)
    setAnalysis(null); setOffer(null); setError('')
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div style={s.app}>
      {/* Global CSS for spinner animation */}
      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Segoe UI', Arial, sans-serif; }
        button:disabled { opacity: 0.55; cursor: not-allowed; }
        a { text-decoration: none; }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #f1f5f9; }
        ::-webkit-scrollbar-thumb { background: #cbd5e0; border-radius: 99px; }
      `}</style>

      {/* Navbar */}
      <nav style={s.nav}>
        <span style={s.navLogo}>⚡ PresalesAI</span>
        <span style={s.navSub}>Génération d'Offres Techniques ICT/ELV</span>
        <span style={s.navPill}>GPT-5.4 · RAG · ChromaDB</span>
        {step > 0 && (
          <button
            onClick={reset}
            style={{
              marginLeft: 16, padding: '5px 14px', borderRadius: 6,
              background: 'rgba(255,255,255,.12)', color: '#fff',
              border: '1px solid rgba(255,255,255,.25)', fontSize: 12, cursor: 'pointer',
            }}
          >
            ↩ Nouveau document
          </button>
        )}
      </nav>

      {/* Stepper */}
      <div style={s.stepper}>
        {STEPS.map((st, i) => (
          <React.Fragment key={st.id}>
            <div
              style={s.step(step === i, i < step)}
              onClick={() => goToStep(i)}
            >
              <div style={s.stepNum(step === i, i < step)}>
                {i < step ? '✓' : i + 1}
              </div>
              <span style={s.stepLabel(step === i)}>
                {st.emoji} {st.label}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <div style={s.stepSep}>›</div>
            )}
          </React.Fragment>
        ))}
      </div>

      {/* Main content */}
      <main style={s.main}>

        {error && (
          <div style={s.alert('error')}>
            ⚠ {error}
            <button
              onClick={() => setError('')}
              style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', color: '#c53030' }}
            >✕</button>
          </div>
        )}

        {/* STEP 0 — Upload */}
        {step === 0 && (
          <div style={{ maxWidth: 600, margin: '0 auto' }}>
            <div style={s.card}>
              <div style={s.cardTitle}>
                📄 Chargement du Cahier des Charges
              </div>
              <UploadZone
                onAnalysis={handleAnalysis}
                loading={loading}
                setLoading={setLoading}
              />
            </div>

            {/* Feature overview */}
            <div style={{ ...s.cols, marginTop: 24, gridTemplateColumns: 'repeat(3, 1fr)' }}>
              {[
                { icon: '🔍', title: 'Extraction IA', desc: 'GPT-5.4 analyse et structure toutes les exigences techniques du document' },
                { icon: '🎯', title: 'Matching Produits', desc: 'Scoring de conformité automatique sur l\'ensemble du catalogue produits' },
                { icon: '📝', title: 'Génération Offre', desc: 'Offre technique complète + BOQ + tableau de conformité exportable DOCX' },
              ].map(f => (
                <div key={f.title} style={{ ...s.card, textAlign: 'center' }}>
                  <div style={{ fontSize: 32, marginBottom: 10 }}>{f.icon}</div>
                  <div style={{ fontWeight: 700, marginBottom: 6, color: '#1a365d' }}>{f.title}</div>
                  <div style={{ fontSize: 13, color: '#718096', lineHeight: 1.6 }}>{f.desc}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* STEP 1 — Requirements */}
        {step === 1 && analysis && (
          <div style={s.cols}>
            <div>
              <RequirementsPanel analysis={analysis} />
            </div>
            <div style={s.card}>
              <div style={s.cardTitle}>📊 Statistiques</div>
              <StatsBlock analysis={analysis} />
              <button
                style={{
                  marginTop: 20, width: '100%', padding: '12px',
                  background: 'linear-gradient(135deg, #1a365d, #2b6cb0)',
                  color: '#fff', border: 'none', borderRadius: 10,
                  fontSize: 14, fontWeight: 700, cursor: 'pointer',
                }}
                onClick={() => setStep(2)}
              >
                Voir les produits recommandés →
              </button>
            </div>
          </div>
        )}

        {/* STEP 2 — Products */}
        {step === 2 && analysis && (
          <ProductsPanel
            analysis={analysis}
            onGenerate={handleGenerate}
            generating={generating}
          />
        )}

        {/* STEP 3 — Offer */}
        {step === 3 && offer && (
          <OfferPanel offer={offer} sessionId={sessionId} />
        )}

      </main>

      {/* Loading overlay */}
      {(loading || generating) && (
        <div style={s.overlay}>
          <div style={s.spinnerBox}>
            <div style={s.spinner} />
            <div style={s.spinText}>
              {loading ? 'Analyse en cours…' : 'Génération de l\'offre…'}
            </div>
            <div style={s.spinSub}>
              {loading
                ? 'GPT-5.4 extrait les exigences et score les produits'
                : 'GPT-4 rédige l\'offre technique complète'
              }
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Stats block ───────────────────────────────────────────────────────────────
function StatsBlock({ analysis }) {
  const reqs = analysis.extracted_requirements || []
  const prods = analysis.recommended_products || []

  // Group by section
  const sections = [...new Set(reqs.map(r => r.section))]

  // Best product compliance
  const best = prods.length > 0
    ? Math.round(prods[0].compliance_score * 100)
    : 0

  const stats = [
    { label: 'Exigences extraites', value: reqs.length, color: '#2b6cb0' },
    { label: 'Sections identifiées', value: sections.length, color: '#6b46c1' },
    { label: 'Produits évalués', value: prods.length, color: '#d97706' },
    { label: 'Meilleur score conformité', value: `${best}%`, color: best >= 90 ? '#38a169' : '#d97706' },
  ]

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
      {stats.map(st => (
        <div key={st.label} style={{
          padding: '14px 16px', borderRadius: 10,
          background: '#f8fafc', border: '1px solid #e2e8f0',
          textAlign: 'center',
        }}>
          <div style={{ fontSize: 26, fontWeight: 800, color: st.color }}>{st.value}</div>
          <div style={{ fontSize: 12, color: '#718096', marginTop: 4 }}>{st.label}</div>
        </div>
      ))}
    </div>
  )
}
