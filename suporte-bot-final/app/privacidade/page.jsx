import Link from 'next/link'

export const metadata = {
  title: 'Política de Privacidade - Suporte Bot',
}

export default function Privacidade() {
  return (
    <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #0a0a0f 0%, #0d0d12 100%)' }}>
      <header style={{ background: 'rgba(22, 27, 34, 0.7)', backdropFilter: 'blur(10px)', borderBottom: '1px solid rgba(255,255,255,0.06)', padding: '16px 0' }}>
        <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '0 16px' }}>
          <Link href="/" style={{ color: '#6c5ce7', textDecoration: 'none', fontSize: '14px', fontWeight: '600' }}>
            ← Voltar
          </Link>
        </div>
      </header>

      <main style={{ maxWidth: '900px', margin: '0 auto', padding: '40px 16px' }}>
        <h1 style={{ fontSize: '40px', fontWeight: '700', marginBottom: '24px', background: 'linear-gradient(135deg, #6c5ce7, #00b894)', backgroundClip: 'text', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
          🔒 Política de Privacidade
        </h1>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', color: '#e2e8f0', lineHeight: '1.8' }}>
          <section>
            <h2 style={{ fontSize: '24px', fontWeight: '700', color: '#e2e8f0', marginBottom: '12px' }}>1. Dados Coletados</h2>
            <p style={{ color: '#94a3b8' }}>Coletamos ID do Discord, nome de usuário, avatar, mensagens e informações de tickets.</p>
          </section>

          <section>
            <h2 style={{ fontSize: '24px', fontWeight: '700', color: '#e2e8f0', marginBottom: '12px' }}>2. Como Usamos</h2>
            <p style={{ color: '#94a3b8' }}>Seus dados são usados para fornecer suporte técnico e melhorar o serviço.</p>
          </section>

          <section>
            <h2 style={{ fontSize: '24px', fontWeight: '700', color: '#e2e8f0', marginBottom: '12px' }}>3. Segurança</h2>
            <p style={{ color: '#94a3b8' }}>Seus dados são armazenados com segurança no Supabase, com criptografia end-to-end.</p>
          </section>

          <p style={{ color: '#64748b', fontSize: '14px', marginTop: '24px' }}>Última atualização: {new Date().toLocaleDateString('pt-BR')}</p>
        </div>
      </main>
    </div>
  )
}
