import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'

const API_BASE = 'http://localhost:5000/api'

export default function App() {
  const [sessionId, setSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [error, setError] = useState('')
  const [isDark, setIsDark] = useState(() => sessionStorage.getItem('studymate_theme') === 'dark')
  const [pastSessions, setPastSessions] = useState([])
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const scrollRef = useRef(null)

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light')
    sessionStorage.setItem('studymate_theme', isDark ? 'dark' : 'light')
  }, [isDark])

  // Reuse the existing session across refreshes (sessionStorage survives a
  // refresh but clears when the tab is closed -- matches "live session" scope).
  useEffect(() => {
    const existingId = sessionStorage.getItem('studymate_session_id')

    if (existingId) {
      setSessionId(existingId)
      // Rehydrate the visible chat from the backend's stored history
      fetch(`${API_BASE}/history/${existingId}`)
        .then((res) => {
          if (!res.ok) throw new Error('Session expired')
          return res.json()
        })
        .then((data) => {
          const restored = data.history.map((turn) => ({
            role: turn.role,
            text: turn.parts[0],
          }))
          setMessages(restored)
        })
        .catch(() => {
          // Backend restarted and lost this session -- start fresh
          sessionStorage.removeItem('studymate_session_id')
          createNewSession()
        })
    } else {
      createNewSession()
    }

    refreshPastSessions()
  }, [])

  function refreshPastSessions() {
    fetch(`${API_BASE}/sessions`)
      .then((res) => res.json())
      .then((data) => setPastSessions(data.sessions))
      .catch(() => {
        /* sidebar is non-critical; fail silently */
      })
  }

  function createNewSession() {
    fetch(`${API_BASE}/session`, { method: 'POST' })
      .then((res) => res.json())
      .then((data) => {
        sessionStorage.setItem('studymate_session_id', data.session_id)
        setSessionId(data.session_id)
      })
      .catch(() => setError('Could not reach the backend. Is it running?'))
  }

  function startNewTopic() {
    refreshPastSessions() // make sure the chat we're leaving shows up in the sidebar
    sessionStorage.removeItem('studymate_session_id')
    setMessages([])
    setError('')
    createNewSession()
  }

  function loadSession(targetId) {
    setError('')
    setSessionId(targetId)
    sessionStorage.setItem('studymate_session_id', targetId)
    fetch(`${API_BASE}/history/${targetId}`)
      .then((res) => res.json())
      .then((data) => {
        const restored = data.history.map((turn) => ({
          role: turn.role,
          text: turn.parts[0],
        }))
        setMessages(restored)
      })
      .catch(() => setError('Could not load that conversation.'))
    setIsSidebarOpen(false)
  }

  function exportChat() {
    if (messages.length === 0) return

    const lines = messages.map((m) => {
      const speaker = m.role === 'user' ? 'You' : 'StudyMate'
      return `${speaker}: ${m.text}`
    })
    const content = lines.join('\n\n')

    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    const timestamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')
    a.href = url
    a.download = `studymate-chat-${timestamp}.txt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, isSending])

  async function sendMessage() {
    const trimmed = input.trim()
    if (!trimmed || !sessionId || isSending) return

    setError('')
    setMessages((prev) => [...prev, { role: 'user', text: trimmed }])
    setInput('')
    setIsSending(true)

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: trimmed }),
      })
      const data = await res.json()

      if (!res.ok) {
        setError(data.detail || 'Something went wrong.')
      } else {
        setMessages((prev) => [...prev, { role: 'model', text: data.reply }])
        refreshPastSessions()
      }
    } catch {
      setError('Network error — check that the backend is running on port 5000.')
    } finally {
      setIsSending(false)
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="page">
      <header className="header">
        <div className="header-mark">SM</div>
        <div className="header-text">
          <h1>StudyMate</h1>
          <p className="subtitle">Your session-aware study buddy</p>
        </div>
        <div className="toolbar">
          <button
            className="icon-button"
            onClick={() => setIsSidebarOpen((o) => !o)}
            title="Past conversations"
          >
            History
          </button>
          <button
            className="icon-button"
            onClick={exportChat}
            disabled={messages.length === 0}
            title="Export chat as text file"
          >
            Export
          </button>
          <button className="icon-button" onClick={startNewTopic} title="Start a new topic">
            New topic
          </button>
          <button
            className="icon-button theme-toggle"
            onClick={() => setIsDark((d) => !d)}
            title="Toggle dark mode"
          >
            {isDark ? '☀️' : '🌙'}
          </button>
        </div>
      </header>

      <main className="chat-shell">
        {isSidebarOpen && (
          <div className="sidebar-overlay" onClick={() => setIsSidebarOpen(false)}>
            <div className="sidebar" onClick={(e) => e.stopPropagation()}>
              <div className="sidebar-header">
                <span>Past conversations</span>
                <button className="icon-button" onClick={() => setIsSidebarOpen(false)}>
                  Close
                </button>
              </div>
              <div className="sidebar-list">
                {pastSessions.length === 0 && (
                  <p className="sidebar-empty">No past conversations yet.</p>
                )}
                {pastSessions.map((s) => (
                  <button
                    key={s.session_id}
                    className={`sidebar-item ${s.session_id === sessionId ? 'active' : ''}`}
                    onClick={() => loadSession(s.session_id)}
                  >
                    {s.title}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        <div className="chat-scroll" ref={scrollRef}>
          {messages.length === 0 && (
            <div className="empty-state">
              <p>Tell me what you're studying and I'll help you work through it.</p>
              <p className="empty-hint">Try: "I'm studying Python loops" or "Quiz me on the water cycle."</p>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} className={`bubble-row ${m.role}`}>
              <div className="bubble">
                {m.role === 'model' ? (
                  <ReactMarkdown>{m.text}</ReactMarkdown>
                ) : (
                  m.text
                )}
              </div>
            </div>
          ))}

          {isSending && (
            <div className="bubble-row model">
              <div className="bubble typing">
                <span></span><span></span><span></span>
              </div>
            </div>
          )}
        </div>

        {error && <div className="error-banner">{error}</div>}

        <div className="composer">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question or share what you're studying..."
            rows={2}
          />
          <button onClick={sendMessage} disabled={!input.trim() || isSending}>
            Send
          </button>
        </div>
      </main>
    </div>
  )
}
