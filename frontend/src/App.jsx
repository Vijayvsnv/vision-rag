import React, { useState, useRef, useEffect } from 'react'

const API = 'https://vision-rag-backend-t58m.onrender.com'
// const API = 'http://127.0.0.1:8000'
const uid = () => Math.random().toString(36).slice(2, 10)

function Tag({ children }) {
  return (
    <span style={{
      display: 'inline-block', padding: '3px 10px', borderRadius: 20,
      background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.2)',
      color: '#6366f1', fontSize: 11, fontFamily: 'var(--font-mono)',
      letterSpacing: '0.03em', whiteSpace: 'nowrap'
    }}>{children}</span>
  )
}

function Spin({ size = 16, color = '#6366f1' }) {
  return <span style={{
    display: 'inline-block', width: size, height: size,
    border: `2px solid rgba(99,102,241,0.15)`, borderTopColor: color,
    borderRadius: '50%', animation: 'spin 0.7s linear infinite', flexShrink: 0
  }} />
}

function TypingDots() {
  return (
    <span style={{ display: 'flex', gap: 4, alignItems: 'center', padding: '4px 2px' }}>
      {[0, 1, 2].map(i => (
        <span key={i} style={{
          width: 7, height: 7, borderRadius: '50%', background: '#6366f1',
          display: 'inline-block', opacity: 0.5,
          animation: `blink 1.2s ease-in-out ${i * 0.2}s infinite`
        }} />
      ))}
    </span>
  )
}

function ImageCard({ img }) {
  const [loaded, setLoaded] = useState(false)
  const [err, setErr] = useState(false)
  const tags = typeof img.tags === 'string' ? img.tags.split(',') : (img.tags || [])
  return (
    <div style={{
      width: 200, background: '#fff', border: '1px solid #e8eaf2',
      borderRadius: 14, overflow: 'hidden',
      boxShadow: '0 2px 12px rgba(0,0,0,0.06)',
      transition: 'transform 0.2s, box-shadow 0.2s',
      animation: 'fadeUp 0.3s ease both'
    }}
      onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-3px)'; e.currentTarget.style.boxShadow = '0 8px 24px rgba(99,102,241,0.15)' }}
      onMouseLeave={e => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = '0 2px 12px rgba(0,0,0,0.06)' }}
    >
      <div style={{ position: 'relative', width: '100%', height: 120, background: '#f0f2f8', overflow: 'hidden' }}>
        {!loaded && !err && (
          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Spin size={18} />
          </div>
        )}
        {err ? (
          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#9ca3af', fontSize: 12 }}>
            No preview
          </div>
        ) : (
          <img
            src={img.image_url.startsWith('http') ? img.image_url : `${API}${img.image_url}`}
            alt=""
            style={{ width: '100%', height: '100%', objectFit: 'cover', display: loaded ? 'block' : 'none' }}
            onLoad={() => setLoaded(true)}
            onError={() => setErr(true)}
          />
        )}
      </div>
      <div style={{ padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 6 }}>
        {img.notes && (
          <p style={{ fontSize: 10, color: '#6b7280', lineHeight: 1.5 }}>
            {img.notes}
          </p>
        )}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 2 }}>
          <span style={{ fontSize: 10, color: '#9ca3af', fontFamily: 'var(--font-mono)' }}>MATCH</span>
          <span style={{ fontSize: 10, color: '#6366f1', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
            {typeof img.score === 'number' ? img.score.toFixed(3) : img.score}
          </span>
        </div>
      </div>
    </div>
  )
}

function ChatMessage({ msg }) {
  const isUser = msg.role === 'user'
  return (
    <div style={{
      display: 'flex', flexDirection: isUser ? 'row-reverse' : 'row',
      alignItems: 'flex-start', gap: 10,
      animation: 'fadeUp 0.25s ease both'
    }}>
      <div style={{
        width: 32, height: 32, borderRadius: 10, flexShrink: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 14, fontWeight: 700,
        background: isUser ? '#6366f1' : '#fff',
        border: isUser ? 'none' : '1.5px solid #e8eaf2',
        color: isUser ? '#fff' : '#6366f1',
        boxShadow: isUser ? '0 2px 8px rgba(99,102,241,0.3)' : '0 1px 4px rgba(0,0,0,0.06)'
      }}>
        {isUser ? 'U' : '✦'}
      </div>
      <div style={{ maxWidth: '72%', display: 'flex', flexDirection: 'column', gap: 10, alignItems: isUser ? 'flex-end' : 'flex-start' }}>
        <div style={{
          padding: '12px 16px', borderRadius: 14, fontSize: 14, lineHeight: 1.65,
          background: isUser ? '#6366f1' : '#fff',
          border: isUser ? 'none' : '1px solid #e8eaf2',
          borderTopLeftRadius: isUser ? 14 : 4,
          borderTopRightRadius: isUser ? 4 : 14,
          color: isUser ? '#fff' : '#1e2132',
          boxShadow: isUser ? '0 4px 12px rgba(99,102,241,0.25)' : '0 1px 4px rgba(0,0,0,0.06)',
          whiteSpace: 'pre-wrap'
        }}>
          {msg.typing ? <TypingDots /> : msg.content}
        </div>
        {msg.images && msg.images.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
            {msg.images.map((img, i) => <ImageCard key={i} img={img} />)}
          </div>
        )}
      </div>
    </div>
  )
}

function UploadModal({ onClose, onUpload, uploading, lastResult }) {
  const [tab, setTab] = useState('file')
  const [url, setUrl] = useState('')
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [notes, setNotes] = useState('')
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
    if (tab === 'url' && url.trim()) onUpload({ url: url.trim(), notes: notes.trim() })
    if (tab === 'file' && file) onUpload({ file, notes: notes.trim() })
  }

  const hasImage = (tab === 'url' && url.trim()) || (tab === 'file' && file)
  const canSubmit = hasImage
  const handleBackdrop = e => { if (e.target === e.currentTarget) onClose() }

  useEffect(() => {
    const handler = e => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const inputStyle = {
    background: '#f6f7fb', border: '1.5px solid #e8eaf2',
    borderRadius: 10, color: '#1e2132', fontSize: 13,
    padding: '10px 14px', outline: 'none', width: '100%',
    transition: 'border-color 0.2s', fontFamily: 'var(--font-body)',
    boxSizing: 'border-box'
  }

  return (
    <div onClick={handleBackdrop} style={{
      position: 'fixed', inset: 0, zIndex: 100,
      background: 'rgba(17,24,39,0.4)', backdropFilter: 'blur(8px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      animation: 'fadeUp 0.15s ease both'
    }}>
      <div style={{
        width: 440, maxWidth: 'calc(100vw - 40px)',
        background: '#fff', border: '1px solid #e8eaf2',
        borderRadius: 20, padding: '28px',
        display: 'flex', flexDirection: 'column', gap: 16,
        boxShadow: '0 20px 60px rgba(0,0,0,0.12)',
        animation: 'fadeUp 0.22s ease both'
      }}>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: 17, color: '#1e2132' }}>Add Image</div>
            <div style={{ fontSize: 12, color: '#9ca3af', marginTop: 2 }}>Upload to visual knowledge base</div>
          </div>
          <button onClick={onClose} style={{
            width: 30, height: 30, borderRadius: 8, border: '1px solid #e8eaf2',
            background: '#f6f7fb', color: '#9ca3af', fontSize: 18,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            transition: 'all 0.2s', cursor: 'pointer'
          }}
            onMouseEnter={e => { e.currentTarget.style.background = '#fee2e2'; e.currentTarget.style.color = '#ef4444'; e.currentTarget.style.borderColor = '#fecaca' }}
            onMouseLeave={e => { e.currentTarget.style.background = '#f6f7fb'; e.currentTarget.style.color = '#9ca3af'; e.currentTarget.style.borderColor = '#e8eaf2' }}
          >×</button>
        </div>

        <div style={{ height: 1, background: '#f0f2f8' }} />

        <div style={{ display: 'flex', background: '#f6f7fb', borderRadius: 10, padding: 4, gap: 4 }}>
          {['file', 'url'].map(t => (
            <button key={t} onClick={() => setTab(t)} style={{
              flex: 1, padding: '7px 0', borderRadius: 7, border: 'none',
              background: tab === t ? '#fff' : 'transparent',
              color: tab === t ? '#6366f1' : '#9ca3af',
              fontSize: 12, fontWeight: 600,
              boxShadow: tab === t ? '0 1px 4px rgba(0,0,0,0.08)' : 'none',
              transition: 'all 0.2s', cursor: 'pointer'
            }}>
              {t === 'file' ? '📁 File Upload' : '🔗 Image URL'}
            </button>
          ))}
        </div>

        {tab === 'url' ? (
          <textarea
            value={url}
            onChange={e => setUrl(e.target.value)}
            placeholder="https://example.com/image.jpg"
            rows={2}
            style={{ ...inputStyle, resize: 'none', lineHeight: 1.5 }}
            onFocus={e => e.target.style.borderColor = '#6366f1'}
            onBlur={e => e.target.style.borderColor = '#e8eaf2'}
          />
        ) : (
          <div onClick={() => fileRef.current.click()} style={{
            background: '#f6f7fb', border: `1.5px dashed ${file ? '#6366f1' : '#d1d5db'}`,
            borderRadius: 10, padding: '20px', textAlign: 'center', cursor: 'pointer',
            transition: 'border-color 0.2s',
            display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8
          }}
            onMouseEnter={e => e.currentTarget.style.borderColor = '#6366f1'}
            onMouseLeave={e => !file && (e.currentTarget.style.borderColor = '#d1d5db')}
          >
            <input ref={fileRef} type="file" accept="image/*" style={{ display: 'none' }} onChange={handleFile} />
            {preview ? (
              <img src={preview} alt="" style={{ width: '100%', maxHeight: 120, objectFit: 'cover', borderRadius: 8 }} />
            ) : (
              <>
                <span style={{ fontSize: 28 }}>🖼️</span>
                <span style={{ fontSize: 13, color: '#6b7280' }}>Click to choose an image</span>
                <span style={{ fontSize: 11, color: '#9ca3af' }}>JPG · PNG · WEBP</span>
              </>
            )}
            {file && <span style={{ fontSize: 11, color: '#6366f1', fontWeight: 600 }}>✓ {file.name.slice(0, 35)}</span>}
          </div>
        )}

        <div style={{ background: '#f0f4ff', borderRadius: 10, padding: '10px 14px', fontSize: 12, color: '#6366f1', display: 'flex', alignItems: 'center', gap: 6 }}>
          <span>✦</span> Description will be auto-generated by AI
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <label style={{ fontSize: 12, fontWeight: 600, color: '#374151' }}>Additional Info <span style={{ color: '#9ca3af', fontWeight: 400 }}>(optional)</span></label>
          <textarea
            value={notes}
            onChange={e => setNotes(e.target.value)}
            placeholder="Type anything — location, date, time, camera, people, event, anything..."
            rows={3}
            style={{ ...inputStyle, resize: 'none', lineHeight: 1.6 }}
            onFocus={e => e.target.style.borderColor = '#6366f1'}
            onBlur={e => e.target.style.borderColor = '#e8eaf2'}
          />
        </div>

        <button onClick={handleSubmit} disabled={!canSubmit || uploading} style={{
          background: canSubmit && !uploading ? '#6366f1' : '#f0f2f8',
          border: 'none', borderRadius: 10, padding: '13px',
          color: canSubmit && !uploading ? '#fff' : '#9ca3af',
          fontWeight: 700, fontSize: 14,
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
          transition: 'all 0.2s', opacity: uploading ? 0.7 : 1,
          cursor: canSubmit && !uploading ? 'pointer' : 'not-allowed',
          boxShadow: canSubmit && !uploading ? '0 4px 14px rgba(99,102,241,0.35)' : 'none'
        }}>
          {uploading ? <><Spin size={15} color="#fff" /> Processing...</> : 'Add to Knowledge Base'}
        </button>

        {lastResult && (
          <div style={{
            background: lastResult.error ? '#fff5f5' : '#f0fdf4',
            border: `1px solid ${lastResult.error ? '#fecaca' : '#bbf7d0'}`,
            borderRadius: 12, padding: 14, display: 'flex', flexDirection: 'column', gap: 8,
            animation: 'fadeUp 0.3s ease both'
          }}>
            {lastResult.error ? (
              <div style={{ color: '#ef4444', fontSize: 13 }}>✗ {lastResult.error}</div>
            ) : (
              <>
                <img src={lastResult.image_url.startsWith('http') ? lastResult.image_url : `${API}${lastResult.image_url}`}
                  alt="" style={{ width: '100%', borderRadius: 8, maxHeight: 80, objectFit: 'cover' }} />
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{ color: '#16a34a', fontSize: 13, fontWeight: 600 }}>✓ Added successfully</span>
                  <button onClick={onClose} style={{ fontSize: 12, color: '#6366f1', background: 'none', border: 'none', fontWeight: 600, cursor: 'pointer' }}>Done →</button>
                </div>
                <p style={{ fontSize: 12, color: '#6b7280', lineHeight: 1.5 }}>{lastResult.description?.slice(0, 100)}...</p>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

const SUGGESTIONS = [
  { text: 'Show me all images', icon: '🖼️' },
  { text: 'Find a portrait photo', icon: '👤' },
  { text: 'What images do you have?', icon: '🔍' },
]

export default function App() {
  const [messages, setMessages] = useState([{
    id: uid(), role: 'assistant',
    content: 'Hi! How can I help you find images today?',
    images: []
  }])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [lastResult, setLastResult] = useState(null)
  const [imageCount, setImageCount] = useState(0)
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [excludedIds, setExcludedIds] = useState([])
  const [activeImage, setActiveImage] = useState(null)
  const bottomRef = useRef()
  const inputRef = useRef()

  const REJECTION_KEYWORDS = [
    'not this', 'wrong', 'different', 'another', 'other one', 'next', 'change',
    'no not', 'not that', 'show another', 'show different', 'not correct',
    'try another', 'other image', 'other picture', 'change image',
    'find another', 'exit', 'exit this', 'leave this', 'new image',
    'new picture', 'search for', 'look for', 'find image', 'find picture'
  ]

  const isRejection = (msg) => {
    const lower = msg.toLowerCase()
    return REJECTION_KEYWORDS.some(kw => lower.includes(kw))
  }

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    fetch(`${API}/images-list`)
      .then(r => r.json())
      .then(d => setImageCount(d.total || 0))
      .catch(() => {})
  }, [])

  const handleUpload = async ({ url, file, notes }) => {
    setUploading(true)
    setLastResult(null)
    try {
      const fd = new FormData()
      if (url) fd.append('image_url', url)
      if (file) fd.append('file', file)
      if (notes) fd.append('notes', notes)

      const res = await fetch(`${API}/ingest`, { method: 'POST', body: fd })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Upload failed')

      setLastResult(data)
      setImageCount(c => c + 1)
      setMessages(m => [...m, {
        id: uid(), role: 'assistant',
        content: `✓ Image added to knowledge base!\n\n"${data.description?.slice(0, 120)}..."\n\nAsk me anything about it.`,
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

    const rejection = isRejection(msg)

    const NEW_SEARCH_KEYWORDS = ['find another', 'exit', 'exit this', 'leave this', 'new image', 'new picture', 'search for', 'look for', 'find image', 'find picture']
    const isNewTopic = NEW_SEARCH_KEYWORDS.some(kw => msg.toLowerCase().includes(kw))

    // New topic → reset everything; same topic rejection → just exclude current image
    const currentExcluded = isNewTopic
      ? []
      : rejection
        ? [...new Set([...excludedIds, ...messages.filter(m => m.images?.length).flatMap(m => m.images.map(i => i.image_id))])]
        : excludedIds

    // Use locked active image for follow-ups; clear on rejection
    const currentActiveImage = rejection ? null : activeImage
    if (rejection) {
      setActiveImage(null)
      if (isNewTopic) setExcludedIds([])
    }

    const userMsg = { id: uid(), role: 'user', content: msg, images: [] }
    const thinkingId = uid()
    const thinkingMsg = { id: thinkingId, role: 'assistant', content: '', typing: true, images: [] }

    setMessages(m => [...m, userMsg, thinkingMsg])
    setLoading(true)

    try {
      const res = await fetch(`${API}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg, history, excluded_ids: currentExcluded, active_image: currentActiveImage })
      })
      const data = await res.json()
      const newImages = data.matched_images || []

      // Lock the first new image as active for follow-up questions
      if (newImages.length && !currentActiveImage) {
        setActiveImage(newImages[0])
        setExcludedIds(prev => [...new Set([...prev, ...newImages.map(i => i.image_id)])])
      }

      // Show image card on fresh search OR when user explicitly asks to show
      const SHOW_KEYWORDS = ['show', 'display', 'show me', 'show this', 'show image', 'show picture', 'let me see', 'see the image', 'see the picture']
      const wantsToSee = SHOW_KEYWORDS.some(kw => msg.toLowerCase().includes(kw))
      const displayImages = currentActiveImage
        ? (wantsToSee ? [currentActiveImage] : [])
        : newImages

      setMessages(m => m.map(x =>
        x.id === thinkingId
          ? { ...x, content: data.answer, typing: false, images: displayImages }
          : x
      ))
    } catch {
      setMessages(m => m.map(x =>
        x.id === thinkingId
          ? { ...x, content: '⚠ Could not reach backend.', typing: false, images: [] }
          : x
      ))
    }
    setLoading(false)
    inputRef.current?.focus()
  }

  const handleKey = e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() }
  }

  const isEmpty = messages.length <= 1

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', background: 'var(--bg)' }}>
      <main style={{
        flex: 1, display: 'flex', flexDirection: 'column',
        height: '100vh', overflow: 'hidden',
        maxWidth: 860, margin: '0 auto', width: '100%'
      }}>

        {/* Header */}
        <div style={{
          padding: '14px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          borderBottom: '1px solid var(--border)', background: '#fff'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{
              width: 34, height: 34, borderRadius: 10, background: '#6366f1',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 16, color: '#fff', boxShadow: '0 2px 8px rgba(99,102,241,0.35)'
            }}>✦</div>
            <div>
              <div style={{ fontWeight: 700, fontSize: 15, color: '#1e2132', letterSpacing: '-0.2px' }}>VisionRAG</div>
              <div style={{ fontSize: 11, color: '#9ca3af' }}>{imageCount} image{imageCount !== 1 ? 's' : ''} in knowledge base</div>
            </div>
          </div>
          <button onClick={() => { setLastResult(null); setShowUploadModal(true) }} style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '8px 18px', borderRadius: 10,
            border: '1.5px solid #e8eaf2', background: '#fff',
            color: '#6366f1', fontSize: 13, fontWeight: 600,
            transition: 'all 0.2s', cursor: 'pointer'
          }}
            onMouseEnter={e => { e.currentTarget.style.background = '#f0f1ff'; e.currentTarget.style.borderColor = '#6366f1'; e.currentTarget.style.boxShadow = '0 2px 12px rgba(99,102,241,0.15)' }}
            onMouseLeave={e => { e.currentTarget.style.background = '#fff'; e.currentTarget.style.borderColor = '#e8eaf2'; e.currentTarget.style.boxShadow = 'none' }}
          >
            <span style={{ fontSize: 16, lineHeight: 1 }}>+</span> Add Image
          </button>
        </div>

        {/* Messages */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '28px 24px', display: 'flex', flexDirection: 'column', gap: 20 }}>
          {isEmpty && (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', paddingTop: 60, gap: 10 }}>
              <div style={{
                width: 56, height: 56, borderRadius: 18, background: '#6366f1',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 26, color: '#fff', boxShadow: '0 4px 16px rgba(99,102,241,0.35)',
                marginBottom: 6
              }}>✦</div>
              <div style={{ fontSize: 26, fontWeight: 700, color: '#1e2132', letterSpacing: '-0.5px' }}>How can I help?</div>
              <div style={{ fontSize: 14, color: '#9ca3af' }}>Search your visual knowledge base</div>
            </div>
          )}
          {messages.map(msg => <ChatMessage key={msg.id} msg={msg} />)}
          <div ref={bottomRef} />
        </div>

        {/* Suggestions */}
        {isEmpty && (
          <div style={{ padding: '0 24px 16px', display: 'flex', gap: 10, flexWrap: 'wrap', justifyContent: 'center' }}>
            {SUGGESTIONS.map(s => (
              <button key={s.text} onClick={() => sendMessage(s.text)} style={{
                background: '#fff', border: '1.5px solid #e8eaf2',
                borderRadius: 12, padding: '10px 18px',
                color: '#374151', fontSize: 13, fontWeight: 500,
                display: 'flex', alignItems: 'center', gap: 7,
                transition: 'all 0.2s', cursor: 'pointer',
                boxShadow: '0 1px 4px rgba(0,0,0,0.05)'
              }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = '#6366f1'; e.currentTarget.style.color = '#6366f1'; e.currentTarget.style.boxShadow = '0 2px 12px rgba(99,102,241,0.12)' }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = '#e8eaf2'; e.currentTarget.style.color = '#374151'; e.currentTarget.style.boxShadow = '0 1px 4px rgba(0,0,0,0.05)' }}
              >
                <span>{s.icon}</span> {s.text}
              </button>
            ))}
          </div>
        )}

        {/* Input */}
        <div style={{
          padding: '16px 24px 20px', borderTop: '1px solid var(--border)',
          background: '#fff', display: 'flex', gap: 10, alignItems: 'flex-end'
        }}>
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Ask about your images... (Enter to send)"
            rows={1}
            style={{
              flex: 1, background: '#f6f7fb', border: '1.5px solid #e8eaf2',
              borderRadius: 12, color: '#1e2132', fontSize: 14,
              padding: '12px 16px', resize: 'none', outline: 'none',
              lineHeight: 1.5, maxHeight: 120, overflowY: 'auto',
              transition: 'border-color 0.2s', fontFamily: 'var(--font-body)'
            }}
            onFocus={e => e.target.style.borderColor = '#6366f1'}
            onBlur={e => e.target.style.borderColor = '#e8eaf2'}
          />
          <button onClick={() => sendMessage()} disabled={loading || !input.trim()} style={{
            width: 44, height: 44, borderRadius: 12, border: 'none', flexShrink: 0,
            background: loading || !input.trim() ? '#f0f2f8' : '#6366f1',
            color: loading || !input.trim() ? '#9ca3af' : '#fff',
            fontSize: 18, display: 'flex', alignItems: 'center', justifyContent: 'center',
            transition: 'all 0.2s', cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
            boxShadow: !loading && input.trim() ? '0 4px 12px rgba(99,102,241,0.35)' : 'none'
          }}>
            {loading ? <Spin size={16} color={input.trim() ? '#fff' : '#9ca3af'} /> : '↑'}
          </button>
        </div>
      </main>

      {showUploadModal && (
        <UploadModal
          onClose={() => setShowUploadModal(false)}
          onUpload={handleUpload}
          uploading={uploading}
          lastResult={lastResult}
        />
      )}
    </div>
  )
}
