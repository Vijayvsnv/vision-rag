import React, { useState, useRef, useEffect, useCallback } from 'react'

const API = 'http://localhost:8000'
const uid = () => Math.random().toString(36).slice(2, 10)

// ─── Noise / grid background ──────────────────────────────
function BgCanvas() {
  const ref = useRef()
  useEffect(() => {
    const el = ref.current
    const ctx = el.getContext('2d')
    const resize = () => { el.width = window.innerWidth; el.height = window.innerHeight; draw() }
    const draw = () => {
      ctx.clearRect(0, 0, el.width, el.height)
      ctx.strokeStyle = 'rgba(94,255,160,0.035)'
      ctx.lineWidth = 0.5
      const step = 48
      for (let x = 0; x < el.width; x += step) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, el.height); ctx.stroke() }
      for (let y = 0; y < el.height; y += step) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(el.width, y); ctx.stroke() }
      // glowing orbs
      const orbs = [
        { x: el.width * 0.15, y: el.height * 0.2, r: 280, c: 'rgba(94,255,160,0.04)' },
        { x: el.width * 0.85, y: el.height * 0.75, r: 220, c: 'rgba(123,97,255,0.05)' },
      ]
      orbs.forEach(o => {
        const g = ctx.createRadialGradient(o.x, o.y, 0, o.x, o.y, o.r)
        g.addColorStop(0, o.c)
        g.addColorStop(1, 'transparent')
        ctx.fillStyle = g
        ctx.beginPath(); ctx.arc(o.x, o.y, o.r, 0, Math.PI * 2); ctx.fill()
      })
    }
    window.addEventListener('resize', resize)
    resize()
    return () => window.removeEventListener('resize', resize)
  }, [])
  return <canvas ref={ref} style={{ position: 'fixed', inset: 0, zIndex: 0, pointerEvents: 'none' }} />
}

// ─── Tag pill ─────────────────────────────────────────────
function Tag({ children }) {
  return (
    <span style={{
      display: 'inline-block', padding: '2px 8px', borderRadius: 20,
      background: 'rgba(94,255,160,0.07)', border: '1px solid rgba(94,255,160,0.18)',
      color: 'var(--accent)', fontSize: 10, fontFamily: 'var(--font-mono)',
      letterSpacing: '0.04em', whiteSpace: 'nowrap'
    }}>{children}</span>
  )
}

// ─── Spinner ──────────────────────────────────────────────
function Spin({ size = 16, color = 'var(--accent)' }) {
  return <span style={{
    display: 'inline-block', width: size, height: size,
    border: `2px solid rgba(94,255,160,0.15)`, borderTopColor: color,
    borderRadius: '50%', animation: 'spin 0.7s linear infinite', flexShrink: 0
  }} />
}

// ─── Typing indicator ─────────────────────────────────────
function TypingDots() {
  return (
    <span style={{ display: 'flex', gap: 4, alignItems: 'center', padding: '2px 0' }}>
      {[0, 1, 2].map(i => (
        <span key={i} style={{
          width: 6, height: 6, borderRadius: '50%', background: 'var(--accent)',
          display: 'inline-block', opacity: 0.4,
          animation: `blink 1.2s ease-in-out ${i * 0.2}s infinite`
        }} />
      ))}
    </span>
  )
}

// ─── Image card (in chat) ─────────────────────────────────
function ImageCard({ img }) {
  const [loaded, setLoaded] = useState(false)
  const [err, setErr] = useState(false)
  const tags = typeof img.tags === 'string' ? img.tags.split(',') : (img.tags || [])
  return (
    <div style={{
      width: 210, background: 'var(--bg3)', border: '1px solid var(--border)',
      borderRadius: 16, overflow: 'hidden',
      transition: 'border-color 0.25s, transform 0.2s',
      animation: 'fadeUp 0.3s ease both'
    }}
      onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(94,255,160,0.35)'; e.currentTarget.style.transform = 'translateY(-2px)' }}
      onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.transform = 'translateY(0)' }}
    >
      {/* image */}
      <div style={{ position: 'relative', width: '100%', height: 130, background: 'var(--bg4)', overflow: 'hidden' }}>
        {!loaded && !err && (
          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Spin size={20} />
          </div>
        )}
        {err ? (
          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text3)', fontSize: 12 }}>
            No preview
          </div>
        ) : (
          <img
            src={`${API}${img.image_url}`}
            alt=""
            style={{ width: '100%', height: '100%', objectFit: 'cover', display: loaded ? 'block' : 'none' }}
            onLoad={() => setLoaded(true)}
            onError={() => setErr(true)}
          />
        )}
      </div>
      {/* meta */}
      <div style={{ padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 6 }}>
        <p style={{ fontSize: 11, color: 'var(--text2)', lineHeight: 1.5, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
          {img.description}
        </p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
          {tags.slice(0, 3).map(t => <Tag key={t}>{t.trim()}</Tag>)}
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 2 }}>
          <span style={{ fontSize: 10, color: 'var(--text3)', fontFamily: 'var(--font-mono)' }}>MATCH</span>
          <span style={{ fontSize: 10, color: 'var(--accent)', fontFamily: 'var(--font-mono)', letterSpacing: '0.05em' }}>
            {typeof img.score === 'number' ? img.score.toFixed(3) : img.score}
          </span>
        </div>
      </div>
    </div>
  )
}

// ─── Single chat message ──────────────────────────────────
function ChatMessage({ msg }) {
  const isUser = msg.role === 'user'
  return (
    <div style={{
      display: 'flex', flexDirection: isUser ? 'row-reverse' : 'row',
      alignItems: 'flex-start', gap: 10,
      animation: 'fadeUp 0.25s ease both'
    }}>
      {/* avatar */}
      <div style={{
        width: 30, height: 30, borderRadius: 8, flexShrink: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 12, fontWeight: 700, letterSpacing: '-0.5px',
        background: isUser ? 'rgba(123,97,255,0.15)' : 'rgba(94,255,160,0.1)',
        border: `1px solid ${isUser ? 'rgba(123,97,255,0.3)' : 'rgba(94,255,160,0.2)'}`,
        color: isUser ? '#a78bfa' : 'var(--accent)'
      }}>
        {isUser ? 'U' : '⬡'}
      </div>

      <div style={{ maxWidth: '74%', display: 'flex', flexDirection: 'column', gap: 10, alignItems: isUser ? 'flex-end' : 'flex-start' }}>
        {/* bubble */}
        <div style={{
          padding: '11px 15px', borderRadius: 12, fontSize: 14, lineHeight: 1.65,
          background: isUser ? 'rgba(123,97,255,0.1)' : 'var(--bg3)',
          border: `1px solid ${isUser ? 'rgba(123,97,255,0.22)' : 'var(--border)'}`,
          borderTopLeftRadius: isUser ? 12 : 3,
          borderTopRightRadius: isUser ? 3 : 12,
          color: 'var(--text)', whiteSpace: 'pre-wrap'
        }}>
          {msg.typing ? <TypingDots /> : msg.content}
        </div>

        {/* image grid */}
        {msg.images && msg.images.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
            {msg.images.map((img, i) => <ImageCard key={i} img={img} />)}
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Sidebar upload panel ─────────────────────────────────
function Sidebar({ onUpload, uploading, lastResult, imageCount }) {
  const [tab, setTab] = useState('file')
  const [url, setUrl] = useState('')
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const fileRef = useRef()

  const handleFile = e => {
    const f = e.target.files[0]
    if (!f) return
    setFile(f)
    const reader = new FileReader()
    reader.onload = ev => setPreview(ev.target.result)
    reader.readAsDataURL(f)
  }

  const handleSubmit = () => {
    if (tab === 'url' && url.trim()) onUpload({ url: url.trim() })
    if (tab === 'file' && file) onUpload({ file })
  }

  const canSubmit = (tab === 'url' && url.trim()) || (tab === 'file' && file)

  return (
    <aside style={{
      width: 290, minWidth: 290, height: '100vh',
      background: 'var(--bg2)', borderRight: '1px solid var(--border)',
      display: 'flex', flexDirection: 'column', padding: '22px 18px', gap: 16,
      position: 'relative', zIndex: 1, overflowY: 'auto'
    }}>
      {/* Brand */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
        <div style={{
          width: 34, height: 34, borderRadius: 9,
          background: 'var(--glow)', border: '1px solid rgba(94,255,160,0.25)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 16, color: 'var(--accent)', flexShrink: 0,
          animation: 'pulse-glow 3s ease infinite'
        }}>⬡</div>
        <div>
          <div style={{ fontWeight: 800, fontSize: 15, letterSpacing: '-0.4px', color: 'var(--text)' }}>VisionRAG</div>
          <div style={{ fontSize: 9, color: 'var(--text3)', fontFamily: 'var(--font-mono)', letterSpacing: '0.12em' }}>IMAGE INTELLIGENCE</div>
        </div>
      </div>

      <div style={{ height: 1, background: 'var(--border)' }} />

      {/* Stats row */}
      <div style={{ display: 'flex', gap: 8 }}>
        {[
          { label: 'IMAGES', val: imageCount },
          { label: 'BACKEND', val: 'LIVE' }
        ].map(s => (
          <div key={s.label} style={{
            flex: 1, background: 'var(--bg3)', border: '1px solid var(--border)',
            borderRadius: 8, padding: '8px 10px', textAlign: 'center'
          }}>
            <div style={{ fontSize: 16, fontWeight: 700, color: s.label === 'BACKEND' ? 'var(--success)' : 'var(--text)' }}>{s.val}</div>
            <div style={{ fontSize: 9, color: 'var(--text3)', fontFamily: 'var(--font-mono)', marginTop: 2 }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* Section */}
      <div style={{ fontSize: 9, color: 'var(--text3)', fontFamily: 'var(--font-mono)', letterSpacing: '0.15em' }}>INGEST IMAGE</div>

      {/* Tab switcher */}
      <div style={{ display: 'flex', background: 'var(--bg3)', borderRadius: 8, border: '1px solid var(--border)', padding: 3, gap: 3 }}>
        {['file', 'url'].map(t => (
          <button key={t} onClick={() => setTab(t)} style={{
            flex: 1, padding: '6px 0', borderRadius: 6, border: 'none',
            background: tab === t ? 'var(--glow)' : 'transparent',
            color: tab === t ? 'var(--accent)' : 'var(--text3)',
            fontSize: 11, fontWeight: 600, letterSpacing: '0.05em',
            transition: 'all 0.2s',
            outline: tab === t ? '1px solid rgba(94,255,160,0.2)' : 'none'
          }}>
            {t === 'file' ? '📁 FILE' : '🔗 URL'}
          </button>
        ))}
      </div>

      {/* Input area */}
      {tab === 'url' ? (
        <textarea
          value={url}
          onChange={e => setUrl(e.target.value)}
          placeholder="https://example.com/photo.jpg"
          rows={3}
          style={{
            background: 'var(--bg3)', border: '1px solid var(--border)',
            borderRadius: 8, color: 'var(--text)', fontSize: 11,
            padding: '10px 12px', resize: 'none', outline: 'none',
            fontFamily: 'var(--font-mono)', lineHeight: 1.5,
            transition: 'border-color 0.2s'
          }}
          onFocus={e => e.target.style.borderColor = 'rgba(94,255,160,0.4)'}
          onBlur={e => e.target.style.borderColor = 'var(--border)'}
        />
      ) : (
        <>
          <div
            onClick={() => fileRef.current.click()}
            style={{
              background: 'var(--bg3)', border: `1px dashed ${file ? 'rgba(94,255,160,0.4)' : 'var(--border2)'}`,
              borderRadius: 8, padding: '16px', textAlign: 'center', cursor: 'pointer',
              transition: 'border-color 0.2s, background 0.2s',
              display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6
            }}
            onMouseEnter={e => e.currentTarget.style.borderColor = 'rgba(94,255,160,0.35)'}
            onMouseLeave={e => !file && (e.currentTarget.style.borderColor = 'var(--border2)')}
          >
            <input ref={fileRef} type="file" accept="image/*" style={{ display: 'none' }} onChange={handleFile} />
            {preview ? (
              <img src={preview} alt="" style={{ width: '100%', maxHeight: 100, objectFit: 'cover', borderRadius: 6 }} />
            ) : (
              <>
                <span style={{ fontSize: 22 }}>🖼️</span>
                <span style={{ fontSize: 11, color: 'var(--text3)' }}>Click to choose image</span>
              </>
            )}
            {file && <span style={{ fontSize: 10, color: 'var(--accent)', fontFamily: 'var(--font-mono)' }}>📎 {file.name.slice(0, 24)}</span>}
          </div>
        </>
      )}

      {/* Upload button */}
      <button
        onClick={handleSubmit}
        disabled={!canSubmit || uploading}
        style={{
          background: canSubmit && !uploading
            ? 'linear-gradient(135deg, var(--accent) 0%, #00b87a 100%)'
            : 'var(--bg4)',
          border: 'none', borderRadius: 8, padding: '11px',
          color: canSubmit && !uploading ? '#05070d' : 'var(--text3)',
          fontWeight: 700, fontSize: 12, letterSpacing: '0.08em',
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
          transition: 'all 0.25s', opacity: uploading ? 0.7 : 1
        }}
      >
        {uploading ? <><Spin size={14} color="#05070d" /> PROCESSING...</> : 'INGEST IMAGE'}
      </button>

      {/* Last result */}
      {lastResult && (
        <div style={{
          background: 'var(--bg3)', border: `1px solid ${lastResult.error ? 'rgba(255,77,109,0.35)' : 'rgba(94,255,160,0.25)'}`,
          borderRadius: 10, padding: 12, display: 'flex', flexDirection: 'column', gap: 8,
          animation: 'fadeUp 0.3s ease both'
        }}>
          {lastResult.error ? (
            <div style={{ color: 'var(--error)', fontSize: 12 }}>✗ {lastResult.error}</div>
          ) : (
            <>
              <img src={`${API}${lastResult.image_url}`} alt=""
                style={{ width: '100%', borderRadius: 6, maxHeight: 100, objectFit: 'cover' }} />
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ color: 'var(--success)', fontSize: 12 }}>✓ Ingested</span>
              </div>
              <p style={{ fontSize: 11, color: 'var(--text2)', lineHeight: 1.5 }}>
                {lastResult.description?.slice(0, 100)}...
              </p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {(lastResult.tags || []).slice(0, 4).map(t => <Tag key={t}>{t}</Tag>)}
              </div>
            </>
          )}
        </div>
      )}

      <div style={{ flex: 1 }} />

      {/* Footer */}
      <div style={{ fontSize: 10, color: 'var(--text3)', fontFamily: 'var(--font-mono)', lineHeight: 1.7 }}>
        <div>STACK: FastAPI · ChromaDB</div>
        <div>CLIP clip-ViT-B-32 · GPT-4o-mini</div>
      </div>
    </aside>
  )
}

// ─── Suggested prompts ────────────────────────────────────
const SUGGESTIONS = [
  'What images do you have?',
  'Show me all images',
  'Describe what you see',
]

// ─── Main App ─────────────────────────────────────────────
export default function App() {
  const [messages, setMessages] = useState([{
    id: uid(), role: 'assistant',
    content: 'Hey! I\'m VisionRAG — your visual memory assistant.\n\nIngest images using the panel on the left, then ask me anything about them. I\'ll search through the visual knowledge base and answer you.\n\nTry: "show me all images" or "do you have any image of X?"',
    images: []
  }])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [lastResult, setLastResult] = useState(null)
  const [imageCount, setImageCount] = useState(0)
  const bottomRef = useRef()
  const inputRef = useRef()

  // auto scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // fetch image count on load
  useEffect(() => {
    fetch(`${API}/images-list`)
      .then(r => r.json())
      .then(d => setImageCount(d.total || 0))
      .catch(() => {})
  }, [])

  const handleUpload = async ({ url, file }) => {
    setUploading(true)
    setLastResult(null)
    try {
      const fd = new FormData()
      if (url) fd.append('image_url', url)
      if (file) fd.append('file', file)

      const res = await fetch(`${API}/ingest`, { method: 'POST', body: fd })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Upload failed')

      setLastResult(data)
      setImageCount(c => c + 1)
      setMessages(m => [...m, {
        id: uid(), role: 'assistant',
        content: `✓ Image ingested!\n\n"${data.description?.slice(0, 120)}..."\n\nAsk me anything about it now.`,
        images: []
      }])
    } catch (e) {
      setLastResult({ error: e.message })
    }
    setUploading(false)
  }

  const sendMessage = async (text) => {
    const msg = text || input.trim()
    if (!msg || loading) return
    setInput('')

    const history = messages
      .filter(m => !m.typing && m.content)
      .slice(-8)
      .map(m => ({ role: m.role, content: m.content }))

    const userMsg = { id: uid(), role: 'user', content: msg, images: [] }
    const thinkingId = uid()
    const thinkingMsg = { id: thinkingId, role: 'assistant', content: '', typing: true, images: [] }

    setMessages(m => [...m, userMsg, thinkingMsg])
    setLoading(true)

    try {
      const res = await fetch(`${API}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg, history })
      })
      const data = await res.json()
      setMessages(m => m.map(x =>
        x.id === thinkingId
          ? { ...x, content: data.answer, typing: false, images: data.matched_images || [] }
          : x
      ))
    } catch {
      setMessages(m => m.map(x =>
        x.id === thinkingId
          ? { ...x, content: '⚠ Could not reach backend. Make sure it\'s running on port 8000.', typing: false, images: [] }
          : x
      ))
    }
    setLoading(false)
    inputRef.current?.focus()
  }

  const handleKey = e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() }
  }

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', position: 'relative' }}>
      <BgCanvas />
      <Sidebar onUpload={handleUpload} uploading={uploading} lastResult={lastResult} imageCount={imageCount} />

      {/* Chat Panel */}
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100vh', position: 'relative', zIndex: 1, overflow: 'hidden' }}>

        {/* Header */}
        <div style={{
          padding: '16px 28px', borderBottom: '1px solid var(--border)',
          background: 'rgba(5,7,13,0.85)', backdropFilter: 'blur(12px)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between'
        }}>
          <div>
            <div style={{ fontSize: 15, fontWeight: 700, letterSpacing: '-0.3px' }}>Visual Search Chat</div>
            <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 2 }}>Ask about your ingested images</div>
          </div>
          <div style={{
            fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--accent)',
            background: 'var(--glow)', border: '1px solid rgba(94,255,160,0.2)',
            borderRadius: 20, padding: '4px 12px', letterSpacing: '0.05em'
          }}>
            gpt-4o-mini · clip-ViT-B-32
          </div>
        </div>

        {/* Messages */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: 18 }}>
          {messages.map(msg => <ChatMessage key={msg.id} msg={msg} />)}
          <div ref={bottomRef} />
        </div>

        {/* Suggestion chips */}
        {messages.length <= 1 && (
          <div style={{ padding: '0 28px 12px', display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {SUGGESTIONS.map(s => (
              <button key={s} onClick={() => sendMessage(s)} style={{
                background: 'var(--bg3)', border: '1px solid var(--border)',
                borderRadius: 20, padding: '6px 14px', color: 'var(--text2)',
                fontSize: 12, transition: 'all 0.2s'
              }}
                onMouseEnter={e => { e.target.style.borderColor = 'rgba(94,255,160,0.3)'; e.target.style.color = 'var(--accent)' }}
                onMouseLeave={e => { e.target.style.borderColor = 'var(--border)'; e.target.style.color = 'var(--text2)' }}
              >{s}</button>
            ))}
          </div>
        )}

        {/* Input bar */}
        <div style={{
          padding: '14px 28px', borderTop: '1px solid var(--border)',
          background: 'rgba(5,7,13,0.9)', backdropFilter: 'blur(12px)',
          display: 'flex', gap: 10, alignItems: 'flex-end'
        }}>
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Ask about your images... (Enter to send, Shift+Enter for newline)"
            rows={1}
            style={{
              flex: 1, background: 'var(--bg3)', border: '1px solid var(--border)',
              borderRadius: 10, color: 'var(--text)', fontSize: 14,
              padding: '11px 16px', resize: 'none', outline: 'none',
              lineHeight: 1.5, maxHeight: 120, overflowY: 'auto',
              transition: 'border-color 0.2s', fontFamily: 'var(--font-body)'
            }}
            onFocus={e => e.target.style.borderColor = 'rgba(94,255,160,0.4)'}
            onBlur={e => e.target.style.borderColor = 'var(--border)'}
          />
          <button
            onClick={() => sendMessage()}
            disabled={loading || !input.trim()}
            style={{
              width: 42, height: 42, borderRadius: 10, border: 'none', flexShrink: 0,
              background: loading || !input.trim()
                ? 'var(--bg4)'
                : 'linear-gradient(135deg, var(--accent) 0%, #00b87a 100%)',
              color: loading || !input.trim() ? 'var(--text3)' : '#05070d',
              fontSize: 18, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center',
              transition: 'all 0.2s', cursor: loading || !input.trim() ? 'not-allowed' : 'pointer'
            }}
          >
            {loading ? <Spin size={16} color={input.trim() ? '#05070d' : 'var(--text3)'} /> : '↑'}
          </button>
        </div>
      </main>
    </div>
  )
}
