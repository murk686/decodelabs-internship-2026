import { useState } from 'react'
import ReactMarkdown from 'react-markdown'

const API_BASE = 'http://localhost:5000/api'

const PLATFORMS = [
  { value: 'linkedin',  label: 'LinkedIn' },
  { value: 'instagram', label: 'Instagram' },
  { value: 'twitter',   label: 'Twitter/X' },
  { value: 'email',     label: 'Email' },
]

const TONES = [
  { value: 'professional', label: 'Professional', temp: 0.2, top_p: 0.80, description: 'Authoritative & polished' },
  { value: 'witty',        label: 'Witty',        temp: 0.9, top_p: 0.95, description: 'Clever & playful' },
  { value: 'casual',       label: 'Casual',       temp: 0.6, top_p: 0.90, description: 'Friendly & conversational' },
  { value: 'urgent',       label: 'Urgent',       temp: 0.3, top_p: 0.85, description: 'Action-driven & FOMO' },
]

export default function App() {
  const [form, setForm] = useState({
    product_name: '',
    description: '',
    platform: 'linkedin',
    tone: 'professional',
  })
  const [result, setResult] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState(false)
  const [isDark, setIsDark] = useState(false)
  const [history, setHistory] = useState([])
  const [activeHistoryIndex, setActiveHistoryIndex] = useState(null)
  const [showHistory, setShowHistory] = useState(false)

  function handleChange(e) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }))
  }

  async function callGenerate() {
    setError('')
    setResult(null)
    setActiveHistoryIndex(null)
    setIsLoading(true)

    try {
      const res = await fetch(`${API_BASE}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      const data = await res.json()
      if (!res.ok) {
        setError(data.detail || 'Something went wrong.')
      } else {
        setResult(data)
        // Add to history with timestamp
        const entry = {
          ...data,
          product_name: form.product_name,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        }
        setHistory((prev) => [entry, ...prev])
      }
    } catch {
      setError('Network error — is the backend running on port 5000?')
    } finally {
      setIsLoading(false)
    }
  }

  async function handleGenerate() {
    if (!form.product_name.trim() || !form.description.trim()) {
      setError('Please fill in both Product Name and Description.')
      return
    }
    await callGenerate()
  }

  // Regenerate uses the same form without validation re-check
  async function handleRegenerate() {
    await callGenerate()
  }

  function handleCopy() {
    const text = result?.copy
    if (!text) return
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  function handleDownload() {
    if (!result) return
    const content = [
      `Product: ${form.product_name}`,
      `Platform: ${result.platform_label}`,
      `Tone: ${result.tone_label} (temp=${result.temperature}, top_p=${result.top_p})`,
      `Generated: ${new Date().toLocaleString()}`,
      '',
      '---',
      '',
      result.copy,
    ].join('\n')

    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    const filename = `${form.product_name.replace(/\s+/g, '_')}_${result.platform_label}_${result.tone_label}.txt`
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  function loadHistoryEntry(entry, index) {
    setResult(entry)
    setActiveHistoryIndex(index)
    setShowHistory(false)
  }

  const selectedTone = TONES.find((t) => t.value === form.tone)
  const displayResult = result

  return (
    <div className="page" data-theme={isDark ? 'dark' : 'light'}>
      {/* Header */}
      <header className="header">
        <div className="header-mark">CF</div>
        <div className="header-text">
          <h1>CopyForge</h1>
          <p className="subtitle">AI-powered copywriting & tone transformer</p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          {history.length > 0 && (
            <button className="icon-button" onClick={() => setShowHistory((s) => !s)}>
              History ({history.length})
            </button>
          )}
          <button className="icon-button theme-toggle" onClick={() => setIsDark((d) => !d)}>
            {isDark ? '☀️' : '🌙'}
          </button>
        </div>
      </header>

      {/* History drawer */}
      {showHistory && (
        <div className="history-panel">
          <div className="history-header">
            <span>Session History</span>
            <button className="icon-button" onClick={() => setShowHistory(false)}>Close</button>
          </div>
          <div className="history-list">
            {history.map((entry, i) => (
              <button
                key={i}
                className={`history-item ${activeHistoryIndex === i ? 'active' : ''}`}
                onClick={() => loadHistoryEntry(entry, i)}
              >
                <span className="history-product">{entry.product_name}</span>
                <span className="history-meta">{entry.platform_label} · {entry.tone_label} · {entry.timestamp}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="layout">
        {/* Left: Form */}
        <section className="form-panel">
          <h2 className="panel-title">Product Details</h2>

          <div className="field">
            <label htmlFor="product_name">Product Name</label>
            <input
              id="product_name"
              name="product_name"
              type="text"
              placeholder="e.g. AuraFlow Earbuds"
              value={form.product_name}
              onChange={handleChange}
            />
          </div>

          <div className="field">
            <label htmlFor="description">Description</label>
            <textarea
              id="description"
              name="description"
              rows={4}
              placeholder="e.g. Premium wireless earbuds with 40hr battery and noise cancellation"
              value={form.description}
              onChange={handleChange}
            />
          </div>

          <div className="field">
            <label>Platform</label>
            <div className="chip-group">
              {PLATFORMS.map((p) => (
                <button
                  key={p.value}
                  className={`chip ${form.platform === p.value ? 'active' : ''}`}
                  onClick={() => setForm((prev) => ({ ...prev, platform: p.value }))}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          <div className="field">
            <label>Tone</label>
            <div className="tone-group">
              {TONES.map((t) => (
                <button
                  key={t.value}
                  className={`tone-card ${form.tone === t.value ? 'active' : ''}`}
                  onClick={() => setForm((prev) => ({ ...prev, tone: t.value }))}
                >
                  <span className="tone-name">{t.label}</span>
                  <span className="tone-desc">{t.description}</span>
                  <span className="tone-temp">temp={t.temp}</span>
                </button>
              ))}
            </div>
          </div>

          {selectedTone && (
            <div className="param-bar">
              <span>temperature <strong>{selectedTone.temp}</strong></span>
              <span>top_p <strong>{selectedTone.top_p.toFixed(2)}</strong></span>
            </div>
          )}

          <button
            className="generate-btn"
            onClick={handleGenerate}
            disabled={isLoading}
          >
            {isLoading ? 'Generating...' : 'Generate Copy'}
          </button>

          {error && <div className="error-banner">{error}</div>}
        </section>

        {/* Right: Output */}
        <section className="output-panel">
          <div className="output-header">
            <h2 className="panel-title">Generated Copy</h2>
            {displayResult && (
              <div style={{ display: 'flex', gap: '8px' }}>
                <button className="icon-button" onClick={handleRegenerate} disabled={isLoading}>
                  Regenerate
                </button>
                <button className="icon-button" onClick={handleDownload}>
                  Download
                </button>
                <button className="icon-button" onClick={handleCopy}>
                  {copied ? 'Copied!' : 'Copy'}
                </button>
              </div>
            )}
          </div>

          {isLoading && (
            <div className="loading-state">
              <div className="spinner" />
              <p>Generating your copy...</p>
            </div>
          )}

          {!isLoading && !displayResult && (
            <div className="empty-output">
              <p>Fill in the form and click <strong>Generate Copy</strong> to see results here.</p>
            </div>
          )}

          {displayResult && !isLoading && (
            <>
              <div className="result-meta">
                <span className="meta-tag">{displayResult.platform_label}</span>
                <span className="meta-tag">{displayResult.tone_label}</span>
                <span className="meta-tag muted">temp={displayResult.temperature}</span>
                <span className="meta-tag muted">top_p={displayResult.top_p}</span>
              </div>
              <div className="result-copy">
                <ReactMarkdown>{displayResult.copy}</ReactMarkdown>
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  )
}

