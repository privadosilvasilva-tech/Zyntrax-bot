export default function Home() {
  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '1rem' }}>
      <header style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '1rem 0',
        borderBottom: '1px solid #1e293b',
        flexWrap: 'wrap',
        gap: '0.5rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '2rem' }}>🤖</span>
          <h1 style={{ margin: 0, fontSize: '1.5rem' }}>Suporte Bot</h1>
        </div>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <span style={{ color: '#4ade80', fontSize: '0.875rem' }}>🟢 Online</span>
          <a href="#" style={{ background: '#2563eb', padding: '0.4rem 1rem', borderRadius: '0.5rem', color: '#fff', textDecoration: 'none' }}>
            Convite
          </a>
          <a href="#" style={{ background: '#1e293b', padding: '0.4rem 1rem', borderRadius: '0.5rem', color: '#e2e8f0', textDecoration: 'none' }}>
            Login
          </a>
        </div>
      </header>

      <main style={{ display: 'flex', gap: '2rem', marginTop: '2rem', flexWrap: 'wrap' }}>
        <section style={{ flex: '2', minWidth: '280px' }}>
          <h2>💬 Chat ao vivo</h2>
          <div style={{
            background: '#1e293b',
            borderRadius: '0.5rem',
            padding: '1rem',
            minHeight: '300px',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.5rem'
          }}>
            <div style={{ color: '#94a3b8', textAlign: 'center' }}>
              Nenhuma mensagem ainda. Faça login para enviar.
            </div>
            <div style={{ display: 'flex', gap: '0.5rem', marginTop: 'auto' }}>
              <input
                type="text"
                placeholder="Digite sua mensagem..."
                style={{
                  flex: 1,
                  padding: '0.5rem',
                  borderRadius: '0.5rem',
                  border: '1px solid #334155',
                  background: '#0f172a',
                  color: '#e2e8f0'
                }}
                disabled
              />
              <button
                style={{
                  padding: '0.5rem 1.5rem',
                  background: '#2563eb',
                  border: 'none',
                  borderRadius: '0.5rem',
                  color: '#fff',
                  cursor: 'pointer'
                }}
                disabled
              >
                Enviar
              </button>
            </div>
          </div>
        </section>

        <section style={{ flex: '1', minWidth: '200px' }}>
          <h2>🎫 Suporte</h2>
          <div style={{
            background: '#1e293b',
            borderRadius: '0.5rem',
            padding: '1rem',
            minHeight: '200px'
          }}>
            <button style={{
              width: '100%',
              padding: '0.5rem',
              background: '#2563eb',
              border: 'none',
              borderRadius: '0.5rem',
              color: '#fff',
              cursor: 'pointer',
              marginBottom: '1rem'
            }}>
              + Criar ticket
            </button>
            <div style={{ color: '#94a3b8', textAlign: 'center' }}>
              Nenhum ticket aberto.
            </div>
          </div>
        </section>
      </main>

      <footer style={{
        marginTop: '3rem',
        paddingTop: '1rem',
        borderTop: '1px solid #1e293b',
        display: 'flex',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '0.5rem',
        fontSize: '0.875rem',
        color: '#94a3b8'
      }}>
        <div>© 2026 Suporte Bot</div>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <a href="/termos">Termos</a>
          <a href="/privacidade">Privacidade</a>
          <a href="#">Discord</a>
        </div>
      </footer>
    </div>
  );
}
