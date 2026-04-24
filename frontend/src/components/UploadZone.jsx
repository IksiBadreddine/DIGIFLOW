import React, { useState, useRef } from 'react'
import { Upload, FileText, AlertCircle } from 'lucide-react'

const s = {
  zone: {
    border: '2px dashed #90cdf4',
    borderRadius: 12,
    padding: '3rem 2rem',
    textAlign: 'center',
    cursor: 'pointer',
    background: '#ebf8ff',
    transition: 'all .2s',
  },
  zoneHover: {
    border: '2px dashed #2b6cb0',
    background: '#bee3f8',
  },
  icon: { margin: '0 auto 1rem', color: '#2b6cb0' },
  title: { fontSize: 18, fontWeight: 700, color: '#2d3748', marginBottom: 6 },
  sub: { color: '#718096', fontSize: 14 },
  file: {
    display: 'flex', alignItems: 'center', gap: 12,
    marginTop: 16, padding: '12px 16px',
    background: '#fff', borderRadius: 8,
    border: '1px solid #e2e8f0',
    fontSize: 14,
  },
  btn: {
    marginTop: 20, padding: '12px 36px',
    background: 'linear-gradient(135deg, #1a365d, #2b6cb0)',
    color: '#fff', border: 'none', borderRadius: 8,
    fontSize: 15, fontWeight: 600, cursor: 'pointer',
    width: '100%',
  },
  progress: {
    marginTop: 16, height: 8, borderRadius: 99,
    background: '#e2e8f0', overflow: 'hidden',
  },
  bar: (pct) => ({
    height: '100%', background: '#2b6cb0', borderRadius: 99,
    transition: 'width .3s', width: `${pct}%`,
  }),
  error: {
    marginTop: 12, padding: '10px 14px',
    background: '#fff5f5', border: '1px solid #fc8181',
    borderRadius: 8, color: '#c53030', fontSize: 13,
    display: 'flex', alignItems: 'center', gap: 8,
  }
}

export default function UploadZone({ onAnalysis, loading, setLoading }) {
  const [file, setFile] = useState(null)
  const [hover, setHover] = useState(false)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState('')
  const ref = useRef()

  function handleDrop(e) {
    e.preventDefault(); setHover(false)
    const f = e.dataTransfer.files[0]
    if (f) validate(f)
  }

  function validate(f) {
    setError('')
    const allowed = ['application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'text/plain']
    if (!allowed.includes(f.type) && !f.name.match(/\.(pdf|docx|txt)$/i)) {
      setError('Format non supporté. Acceptés : PDF, DOCX, TXT')
      return
    }
    if (f.size > 20 * 1024 * 1024) {
      setError('Fichier trop volumineux (max 20 Mo)')
      return
    }
    setFile(f)
  }

  async function handleSubmit() {
    if (!file) return
    setError(''); setLoading(true); setProgress(0)
    try {
      const { analyzeDocument } = await import('../services/api.js')
      const result = await analyzeDocument(file, setProgress)
      onAnalysis(result)
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Erreur serveur')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div
        style={{ ...s.zone, ...(hover ? s.zoneHover : {}) }}
        onDragOver={e => { e.preventDefault(); setHover(true) }}
        onDragLeave={() => setHover(false)}
        onDrop={handleDrop}
        onClick={() => ref.current.click()}
      >
        <Upload size={40} style={s.icon} />
        <div style={s.title}>Déposez votre Cahier des Charges ici</div>
        <div style={s.sub}>ou cliquez pour parcourir — PDF, DOCX, TXT (max 20 Mo)</div>
        <input ref={ref} type="file" accept=".pdf,.docx,.txt"
          style={{ display: 'none' }}
          onChange={e => e.target.files[0] && validate(e.target.files[0])} />
      </div>

      {file && (
        <div style={s.file}>
          <FileText size={20} color="#2b6cb0" />
          <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {file.name}
          </span>
          <span style={{ color: '#718096', fontSize: 12 }}>
            {(file.size / 1024).toFixed(0)} Ko
          </span>
        </div>
      )}

      {error && (
        <div style={s.error}>
          <AlertCircle size={16} /> {error}
        </div>
      )}

      {loading && progress > 0 && (
        <div style={s.progress}>
          <div style={s.bar(progress)} />
        </div>
      )}

      <button style={s.btn} onClick={handleSubmit} disabled={!file || loading}>
        {loading ? '⏳ Analyse en cours…' : '🔍 Analyser le document'}
      </button>
    </div>
  )
}
