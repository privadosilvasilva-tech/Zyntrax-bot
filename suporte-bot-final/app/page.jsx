'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { FaDiscord, FaUser, FaSignOutAlt, FaPaperPlane, FaTicketAlt, FaCog, FaHeart, FaThumbsUp } from 'react-icons/fa'

export default function Home() {
  const [messages, setMessages] = useState([])
  const [newMessage, setNewMessage] = useState('')
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(false)
  const [botOnline, setBotOnline] = useState(true)

  useEffect(() => {
    checkAuth()
    simulateRealtime()
  }, [])

  const checkAuth = async () => {
    try {
      const res = await fetch('/api/auth/me')
      if (res.ok) {
        const data = await res.json()
        setUser(data)
        setIsLoggedIn(true)
      }
    } catch (err) {
      console.error(err)
    }
  }

  const simulateRealtime = () => {
    setMessages([
      {
        id: 1,
        username: 'Suporte Bot',
        avatar: '🤖',
        content: 'Bem-vindo ao chat de suporte! Como posso ajudar?',
        timestamp: new Date(),
        likes: 0,
        gostei: 0,
        isFounder: false,
      },
    ])
  }

  const sendMessage = async () => {
    if (!newMessage.trim() || !isLoggedIn || loading) return

    setLoading(true)
    const msg = {
      id: Date.now(),
      username: user?.username,
      avatar: user?.avatar,
      content: newMessage,
      timestamp: new Date(),
      likes: 0,
      gostei: 0,
      isFounder: user?.id === process.env.NEXT_PUBLIC_FOUNDER_ID,
    }

    setMessages([...messages, msg])
    setNewMessage('')
    setLoading(false)
  }

  const toggleLike = (id) => {
    setMessages(
      messages.map((msg) =>
        msg.id === id ? { ...msg, likes: msg.likes + 1 } : msg
      )
    )
  }

  return (
    <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #0a0a0f 0%, #0d0d12 100%)' }}>
      {/* Header */}
      <header style={{ background: 'rgba(22, 27, 34, 0.7)', backdropFilter: 'blur(10px)', borderBottom: '1px solid rgba(255,255,255,0.06)', padding: '16px 0', position: 'sticky', top: 0, zIndex: 100 }}>
        <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '0 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h1 style={{ fontSize: '24px', fontWeight: 700, background: 'linear-gradient(135deg, #6c5ce7, #00b894)', backgroundClip: 'text', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            🤖 Suporte Bot
          </h1>

          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px', background: 'rgba(108, 92, 231, 0.1)', borderRadius: '8px', border: '1px solid rgba(108, 92, 231, 0.3)' }}>
              <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#00b894', animation: 'pulse 2s infinite' }} />
              <span style={{ fontSize: '14px', color: '#00b894' }}>Online</span>
            </div>

            {isLoggedIn ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px', background: 'rgba(245, 158, 11, 0.1)', borderRadius: '8px' }}>
                  {user?.avatar && <img src={user.avatar} alt="avatar" style={{ width: '24px', height: '24px', borderRadius: '50%' }} />}
                  <span style={{ fontSize: '14px', fontWeight: '600' }}>{user?.username}</span>
                </div>

                {user?.id === process.env.NEXT_PUBLIC_FOUNDER_ID && (
                  <Link href="/admin" style={{ padding: '8px 16px', background: '#b91c1c', borderRadius: '8px', color: 'white', fontSize: '14px', fontWeight: '600', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <FaCog size={16} /> Admin
                  </Link>
                )}

                <a href="/api/auth/logout" style={{ padding: '8px 16px', background: 'rgba(239, 68, 68, 0.2)', borderRadius: '8px', color: '#ef4444', fontSize: '14px', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                  <FaSignOutAlt size={16} /> Sair
                </a>
              </div>
            ) : (
              <a href="/api/auth/discord" style={{ padding: '8px 16px', background: '#6c5ce7', borderRadius: '8px', color: 'white', fontSize: '14px', fontWeight: '600', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                <FaDiscord size={16} /> Login Discord
              </a>
            )}

            <a href="https://discord.com/oauth2/authorize?client_id=1540163536406192148&scope=bot&permissions=8" style={{ padding: '8px 16px', background: '#5865f2', borderRadius: '8px', color: 'white', fontSize: '14px', fontWeight: '600', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <FaDiscord size={16} /> Convite
            </a>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main style={{ maxWidth: '1280px', margin: '0 auto', padding: '24px 16px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '24px' }}>
          {/* Chat Section */}
          <div style={{ background: 'rgba(22, 27, 34, 0.7)', backdropFilter: 'blur(10px)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.06)', display: 'flex', flexDirection: 'column', height: '600px' }}>
            <div style={{ background: 'rgba(28, 35, 51, 0.5)', padding: '16px', borderBottom: '1px solid rgba(255,255,255,0.06)', borderTopLeftRadius: '12px', borderTopRightRadius: '12px' }}>
              <h2 style={{ fontSize: '18px', fontWeight: '600', margin: 0 }}>💬 Chat ao Vivo</h2>
            </div>

            <div style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {messages.length === 0 ? (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#94a3b8' }}>
                  Carregando mensagens...
                </div>
              ) : (
                messages.map((msg) => (
                  <div key={msg.id} style={{ background: 'rgba(51, 65, 85, 0.5)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)', animation: 'slideUp 0.3s ease' }}>
                    <div style={{ display: 'flex', gap: '8px', marginBottom: '8px', alignItems: 'center' }}>
                      <div style={{ fontSize: '24px' }}>{msg.avatar}</div>
                      <div>
                        <span style={{ fontWeight: '600', fontSize: '14px' }}>
                          {msg.isFounder && '⭐ '}
                          {msg.username}
                          {msg.isFounder && ' [FUNDADOR]'}
                        </span>
                        <span style={{ fontSize: '12px', color: '#94a3b8', marginLeft: '8px' }}>
                          {msg.timestamp.toLocaleTimeString('pt-BR')}
                        </span>
                      </div>
                    </div>
                    <p style={{ fontSize: '14px', margin: '0 0 8px 0' }}>{msg.content}</p>
                    <div style={{ display: 'flex', gap: '12px', fontSize: '12px' }}>
                      <button onClick={() => toggleLike(msg.id)} style={{ background: 'transparent', color: '#94a3b8', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px', padding: 0, border: 'none', fontSize: '12px' }}>
                        <FaHeart size={14} /> {msg.likes}
                      </button>
                      <button style={{ background: 'transparent', color: '#94a3b8', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px', padding: 0, border: 'none', fontSize: '12px' }}>
                        <FaThumbsUp size={14} /> Gostei
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>

            {isLoggedIn ? (
              <div style={{ borderTop: '1px solid rgba(255,255,255,0.06)', padding: '16px', display: 'flex', gap: '8px' }}>
                <input
                  type="text"
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                  placeholder="Digite sua mensagem..."
                  style={{ flex: 1, background: 'rgba(28, 35, 51, 0.7)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '8px', padding: '10px 12px', fontSize: '14px', color: '#e2e8f0' }}
                />
                <button onClick={sendMessage} disabled={loading} style={{ padding: '10px 16px', background: '#6c5ce7', borderRadius: '8px', color: 'white', fontSize: '14px', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', opacity: loading ? 0.5 : 1 }}>
                  <FaPaperPlane size={14} /> Enviar
                </button>
              </div>
            ) : (
              <div style={{ borderTop: '1px solid rgba(255,255,255,0.06)', padding: '16px', textAlign: 'center', fontSize: '14px', color: '#94a3b8' }}>
                Faça login para enviar mensagens
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {/* Support */}
            <div style={{ background: 'rgba(22, 27, 34, 0.7)', backdropFilter: 'blur(10px)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.06)', padding: '16px' }}>
              <h2 style={{ fontSize: '16px', fontWeight: '600', margin: '0 0 12px 0' }}>🎫 Suporte</h2>
              <button style={{ width: '100%', padding: '10px 16px', background: '#10b981', borderRadius: '8px', color: 'white', fontSize: '14px', fontWeight: '600', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                <FaTicketAlt size={14} /> Criar Ticket
              </button>
            </div>

            {/* Links */}
            <Link href="/termos" style={{ background: 'rgba(22, 27, 34, 0.7)', backdropFilter: 'blur(10px)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.06)', padding: '16px', textAlign: 'center', fontSize: '14px', fontWeight: '600', color: '#e2e8f0', textDecoration: 'none', transition: 'all 0.2s' }}>
              📋 Termos de Serviço
            </Link>

            <Link href="/privacidade" style={{ background: 'rgba(22, 27, 34, 0.7)', backdropFilter: 'blur(10px)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.06)', padding: '16px', textAlign: 'center', fontSize: '14px', fontWeight: '600', color: '#e2e8f0', textDecoration: 'none', transition: 'all 0.2s' }}>
              🔒 Política de Privacidade
            </Link>
          </div>
        </div>
      </main>
    </div>
  )
}
