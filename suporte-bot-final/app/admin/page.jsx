'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { FaArrowLeft, FaTrash, FaPlus } from 'react-icons/fa'

export default function Admin() {
  const [isAuthorized, setIsAuthorized] = useState(false)
  const [userId, setUserId] = useState('')
  const [selectedTag, setSelectedTag] = useState('VIP')
  const [taggedUsers, setTaggedUsers] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    checkAuthorization()
  }, [])

  const checkAuthorization = async () => {
    try {
      const res = await fetch('/api/auth/me')
      if (res.ok) {
        const user = await res.json()
        if (user.id === process.env.NEXT_PUBLIC_FOUNDER_ID) {
          setIsAuthorized(true)
          loadTaggedUsers()
        }
      }
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const loadTaggedUsers = () => {
    setTaggedUsers([
      {
        id: '123456789',
        tag: 'Admin',
        addedAt: new Date().toLocaleString('pt-BR'),
      },
    ])
  }

  const addTag = () => {
    if (!userId.trim()) return

    const newUser = {
      id: userId,
      tag: selectedTag,
      addedAt: new Date().toLocaleString('pt-BR'),
    }

    setTaggedUsers([...taggedUsers, newUser])
    setUserId('')
  }

  const removeTag = (id) => {
    setTaggedUsers(taggedUsers.filter((u) => u.id !== id))
  }

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #0a0a0f 0%, #0d0d12 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ fontSize: '18px', color: '#94a3b8' }}>Carregando...</div>
      </div>
    )
  }

  if (!isAuthorized) {
    return (
      <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #0a0a0f 0%, #0d0d12 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center', color: '#ef4444' }}>
          <p style={{ fontSize: '24px', fontWeight: '700', marginBottom: '12px' }}>Acesso Negado</p>
          <p style={{ color: '#94a3b8' }}>Você não tem permissão para acessar este painel.</p>
          <Link href="/" style={{ marginTop: '16px', color: '#6c5ce7', textDecoration: 'none', fontWeight: '600' }}>
            Voltar para home
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #0a0a0f 0%, #0d0d12 100%)' }}>
      <header style={{ background: 'rgba(22, 27, 34, 0.7)', backdropFilter: 'blur(10px)', borderBottom: '1px solid rgba(255,255,255,0.06)', padding: '16px 0' }}>
        <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '0 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h1 style={{ fontSize: '24px', fontWeight: '700', color: '#e2e8f0' }}>⚙️ Painel Administrativo</h1>
          <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#6c5ce7', textDecoration: 'none', fontSize: '14px', fontWeight: '600' }}>
            <FaArrowLeft size={14} /> Voltar
          </Link>
        </div>
      </header>

      <main style={{ maxWidth: '1280px', margin: '0 auto', padding: '24px 16px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
          {/* Adicionar TAG */}
          <div style={{ background: 'rgba(22, 27, 34, 0.7)', backdropFilter: 'blur(10px)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.06)', padding: '24px' }}>
            <h2 style={{ fontSize: '20px', fontWeight: '700', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <FaPlus size={18} /> Adicionar TAG
            </h2>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '14px', fontWeight: '600', marginBottom: '8px', color: '#94a3b8' }}>ID do Discord</label>
                <input type="text" value={userId} onChange={(e) => setUserId(e.target.value)} placeholder="Cole o ID do Discord aqui" style={{ width: '100%', padding: '10px 12px', background: 'rgba(28, 35, 51, 0.7)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '8px', color: '#e2e8f0', fontSize: '14px' }} />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '14px', fontWeight: '600', marginBottom: '8px', color: '#94a3b8' }}>Selecione a TAG</label>
                <select value={selectedTag} onChange={(e) => setSelectedTag(e.target.value)} style={{ width: '100%', padding: '10px 12px', background: 'rgba(28, 35, 51, 0.7)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '8px', color: '#e2e8f0', fontSize: '14px' }}>
                  <option value="VIP">VIP</option>
                  <option value="Admin">Admin</option>
                  <option value="Moderador">Moderador</option>
                  <option value="Support">Support</option>
                  <option value="Fundador">Fundador</option>
                </select>
              </div>

              <button onClick={addTag} style={{ width: '100%', padding: '10px 16px', background: '#10b981', border: 'none', borderRadius: '8px', color: 'white', fontSize: '14px', fontWeight: '600', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', marginTop: '8px' }}>
                <FaPlus size={14} /> Adicionar TAG
              </button>
            </div>
          </div>

          {/* Lista de Usuários */}
          <div style={{ background: 'rgba(22, 27, 34, 0.7)', backdropFilter: 'blur(10px)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.06)', padding: '24px' }}>
            <h2 style={{ fontSize: '20px', fontWeight: '700', marginBottom: '16px' }}>👥 Usuários com TAGs ({taggedUsers.length})</h2>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', maxHeight: '400px', overflowY: 'auto' }}>
              {taggedUsers.length === 0 ? (
                <p style={{ color: '#94a3b8', textAlign: 'center', padding: '24px 0' }}>Nenhum usuário com TAG</p>
              ) : (
                taggedUsers.map((user) => (
                  <div key={user.id} style={{ background: 'rgba(28, 35, 51, 0.7)', padding: '16px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <p style={{ fontWeight: '600', fontSize: '14px', marginBottom: '4px', color: '#e2e8f0' }}>🏷️ {user.tag}</p>
                      <p style={{ fontSize: '12px', color: '#94a3b8' }}>ID: {user.id}</p>
                      <p style={{ fontSize: '12px', color: '#64748b' }}>Adicionado: {user.addedAt}</p>
                    </div>
                    <button onClick={() => removeTag(user.id)} style={{ padding: '8px 12px', background: '#ef4444', border: 'none', borderRadius: '6px', color: 'white', fontSize: '12px', fontWeight: '600', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <FaTrash size={12} /> Remover
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
