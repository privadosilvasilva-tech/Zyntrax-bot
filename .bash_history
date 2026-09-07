        .flow-visual { display: flex; justify-content: center; gap: 1rem; margin: 2rem 0; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: var(--accent); opacity: 0.8; }
        section { margin-bottom: 3rem; padding: 2rem; background: var(--surface); border-radius: 8px; border: 1px solid var(--border); }
        h2 { color: white; margin-bottom: 1rem; font-size: 1.4rem; }
        footer { text-align: center; padding: 4rem 0; color: var(--text); opacity: 0.5; font-size: 0.8rem; }
    </style>
</head>
<body>
    <header><div class="nav-container"><div class="logo">ZYNTRAX_PRIVACY</div></div></header>
    <div class="main-wrapper">
        <div class="hero-card">
            <h1>Política de Privacidade</h1>
            <p>Transparência sobre como o Zyntrax coleta, utiliza e protege informações.</p>
            <div class="flow-visual"><span>COLETA</span> → <span>PROCESSAMENTO</span> → <span>ARMAZENAMENTO</span> → <span>EXCLUSÃO</span></div>
        </div>
        <div id="privacy-content"></div>
    </div>
    <footer><p>Zyntrax | Fundado por Nix Founder | © 2026 Zyntrax.</p></footer>
    <script>
        const privacySections = ["1. Introdução", "2. Informações Processadas", "3. Minimização de Dados", "4. Segurança", "5. Direitos dos Usuários", "6. Contato"];
        const container = document.getElementById('privacy-content');
        privacySections.forEach(title => {
            const div = document.createElement('div'); div.innerHTML = `<h2>${title}</h2><p>Texto oficial da política de privacidade Zyntrax...</p>`; container.appendChild(div);
        });
    </script>
</body>
</html>
PRIVACY_EOF

# 3. Compactando em ZIPs
zip -r zyntrax-terms.zip zyntrax-terms/
zip -r zyntrax-privacy.zip zyntrax-privacy/
echo "✅ Zips criados com sucesso! Procure por 'zyntrax-terms.zip' e 'zyntrax-privacy.zip' na pasta /sdcard/Download ou na raiz do Termux."
cd ~ && mv zyntrax-terms.zip zyntrax-privacy.zip /sdcard/Download/ && echo "✅ Arquivos movidos com sucesso para a pasta Download!"
<html lang="pt-BR">
<head>
</head>
<body>
</body>
</html>
cd ~ && rm -rf zyntrax-terms && mkdir -p zyntrax-terms
cat > zyntrax-terms/index.html << 'TERMS_EOF'
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Termos de Uso | Zyntrax</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root { --bg: #0a0a0f; --surface: rgba(255, 255, 255, 0.03); --border: rgba(255, 255, 255, 0.08); --text: #e2e8f0; --text-muted: #94a3b8; --accent: #6366f1; }
        * { margin: 0; padding: 0; box-sizing: border-box; scroll-behavior: smooth; }
        body { font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); line-height: 1.7; overflow-x: hidden; }
        header { position: fixed; top: 0; width: 100%; z-index: 100; background: rgba(10, 10, 15, 0.85); backdrop-filter: blur(16px); border-bottom: 1px solid var(--border); }
        .nav-container { max-width: 1200px; margin: 0 auto; padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center; }
        .logo { font-weight: 700; font-size: 1.25rem; letter-spacing: -0.02em; color: white; }
        .version-badge { background: var(--surface); border: 1px solid var(--border); padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; color: var(--accent); font-weight: 600; }
        .main-wrapper { max-width: 1200px; margin: 80px auto 0; display: grid; grid-template-columns: 280px 1fr; gap: 4rem; padding: 2rem; min-height: calc(100vh - 200px); }
        aside { position: sticky; top: 100px; height: calc(100vh - 120px); overflow-y: auto; scrollbar-width: thin; scrollbar-color: var(--border) transparent; }
        .sidebar-link { display: block; padding: 8px 0; color: var(--text-muted); text-decoration: none; font-size: 0.9rem; border-left: 2px solid transparent; padding-left: 1rem; transition: all 0.3s ease; margin-bottom: 4px; }
        .sidebar-link:hover, .sidebar-link.active { color: white; border-left-color: var(--accent); background: linear-gradient(90deg, rgba(99, 102, 241, 0.1), transparent); }
        main { min-width: 0; }
        h1 { font-size: clamp(2rem, 5vw, 3.5rem); font-weight: 800; margin-bottom: 1rem; background: linear-gradient(to right, #fff, #94a3b8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; line-height: 1.2; }
        .hero-sub { font-size: 1.1rem; color: var(--text-muted); margin-bottom: 2rem; max-width: 600px; }
        .last-update { display: inline-block; background: var(--surface); padding: 6px 12px; border-radius: 6px; font-size: 0.8rem; color: var(--text-muted); margin-bottom: 3rem; border: 1px solid var(--border); }
        .acceptance-card { background: linear-gradient(145deg, rgba(99, 102, 241, 0.08), rgba(255,255,255,0.02)); border: 1px solid rgba(99, 102, 241, 0.3); padding: 2rem; border-radius: 16px; margin-bottom: 4rem; }
        section { margin-bottom: 4rem; scroll-margin-top: 100px; animation: fadeIn 0.5s ease; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        h2 { font-size: 1.5rem; margin-bottom: 1.5rem; color: white; border-bottom: 1px solid var(--border); padding-bottom: 0.75rem; display: flex; align-items: center; gap: 10px; }
        h2::before { content: ''; width: 4px; height: 24px; background: var(--accent); border-radius: 2px; }
        p, li { color: var(--text-muted); margin-bottom: 1rem; font-size: 1rem; }
        ul { padding-left: 1.5rem; margin-bottom: 1.5rem; list-style-type: none; }
        li { position: relative; padding-left: 1.5rem; }
        li::before { content: '•'; color: var(--accent); position: absolute; left: 0; font-weight: bold; }
        .btn-support { display: inline-flex; align-items: center; gap: 8px; background: var(--accent); color: white; padding: 14px 28px; border-radius: 8px; text-decoration: none; font-weight: 600; transition: all 0.3s; margin-top: 1rem; border: 1px solid rgba(255,255,255,0.1); }
        .btn-support:hover { transform: translateY(-2px); box-shadow: 0 10px 30px -10px rgba(99, 102, 241, 0.3); background: #4f46e5; }
        footer { border-top: 1px solid var(--border); padding: 4rem 2rem; text-align: center; color: var(--text-muted); font-size: 0.9rem; margin-top: 4rem; background: rgba(0,0,0,0.2); }
        footer h3 { color: white; margin-bottom: 0.5rem; font-size: 1.2rem; }
        .footer-links { margin-top: 1.5rem; display: flex; justify-content: center; gap: 1.5rem; flex-wrap: wrap; }
        .footer-links a { color: var(--text-muted); text-decoration: none; transition: 0.3s; font-size: 0.85rem; }
        .footer-links a:hover { color: var(--accent); }
        @media (max-width: 900px) { .main-wrapper { grid-template-columns: 1fr; gap: 2rem; padding: 1.5rem; margin-top: 70px; } aside { display: none; } h1 { font-size: 2.2rem; } .acceptance-card { padding: 1.5rem; } .nav-container { padding: 1rem 1.5rem; } }
        @media (max-width: 480px) { h1 { font-size: 1.8rem; } h2 { font-size: 1.3rem; } p, li { font-size: 0.95rem; } .btn-support { width: 100%; justify-content: center; } }
    </style>
</head>
<body>
    <header><div class="nav-container"><div class="logo">ZYNTRAX</div><span class="version-badge">v1.0</span></div></header>
    <div class="main-wrapper">
        <aside id="sidebar"></aside>
        <main>
            <h1>Termos de Uso</h1>
            <p class="hero-sub">As regras que estabelecem como o Zyntrax pode ser utilizado de forma segura, responsável e transparente.</p>
            <span class="last-update">Última atualização: 05 de setembro de 2026</span>
            <div class="acceptance-card"><h3>Aceitação dos Termos</h3><p style="margin-top: 10px;">Ao utilizar, adicionar ou interagir com o Zyntrax, você declara que leu e compreendeu estes Termos de Uso e concorda em respeitá-los integralmente.</p></div>
            <div id="content-area"></div>
        </main>
    </div>
    <footer>
        <h3>ZYNTRAX</h3>
        <p>Sistema de automação e gerenciamento para comunidades Discord.</p>
        <p>Fundado por Nix Founder</p>
        <p style="margin-top: 1rem; opacity: 0.7;">© 2026 Zyntrax. Todos os direitos reservados.</p>
        <div class="footer-links"><a href="#">Termos de Uso</a><a href="../zyntrax-privacidade">Política de Privacidade</a><a href="#">Suporte</a></div>
    </footer>
    <script>
        const termsData = [
            { id: 'sobre', title: '1. Sobre o Zyntrax', content: `<p>O Zyntrax é uma solução desenvolvida para auxiliar na administração, organização, atendimento e automação de comunidades hospedadas na plataforma Discord.</p><p>Dependendo da configuração realizada pelos administradores, o Zyntrax pode disponibilizar recursos como:</p><ul><li>Sistema de tickets;</li><li>Atendimento e suporte;</li><li>Moderação;</li><li>Automação;</li><li>Sistemas de economia virtual;</li><li>Loja;</li><li>Gerenciamento de produtos;</li><li>Sistemas de recompensas;</li><li>Integrações;</li><li>Recursos administrativos;</li><li>Ferramentas de organização de servidores;</li><li>Outros recursos disponibilizados pelo projeto.</li></ul><p>Os recursos disponíveis podem variar de acordo com a versão do Zyntrax, configuração do servidor e atualizações realizadas pelo projeto.</p>` },
            { id: 'aceitacao', title: '2. Aceitação dos Termos', content: `<p>Ao utilizar o Zyntrax, você concorda com estes Termos de Uso.</p><p>Caso não concorde com qualquer parte deste documento, deverá interromper a utilização do serviço.</p><p>O administrador de um servidor também é responsável por garantir que a utilização do Zyntrax dentro de sua comunidade esteja de acordo com estes Termos.</p><p>A utilização contínua do serviço após alterações nos Termos poderá representar a aceitação da versão atualizada.</p>` },
            { id: 'requisitos', title: '3. Requisitos de utilização', content: `<p>Para utilizar determinadas funcionalidades do Zyntrax, pode ser necessário possuir uma conta válida no Discord e ter as permissões necessárias dentro do servidor.</p><p>O usuário deve:</p><ul><li>Utilizar o serviço de maneira legítima;</li><li>Respeitar as regras do Discord;</li><li>Respeitar as regras do servidor em que o Zyntrax está instalado;</li><li>Não tentar explorar falhas;</li><li>Não tentar obter acesso não autorizado;</li><li>Não utilizar o serviço para atividades ilícitas;</li><li>Não interferir deliberadamente no funcionamento do sistema.</li></ul>` },
            { id: 'responsabilidade', title: '4. Responsabilidade do usuário', content: `<p>Cada usuário é responsável pelas ações realizadas utilizando sua conta Discord e pelas interações realizadas com o Zyntrax.</p><p>O Zyntrax não se responsabiliza por decisões tomadas por administradores de servidores utilizando as ferramentas disponibilizadas pelo sistema.</p><p>Administradores são responsáveis por configurar adequadamente os recursos e verificar as permissões concedidas ao bot.</p>` },
            { id: 'proibido', title: '5. Uso proibido', content: `<p>É proibido utilizar o Zyntrax para:</p><ul><li>Fraudes;</li><li>Golpes;</li><li>Tentativas de invasão;</li><li>Exploração de vulnerabilidades;</li><li>Distribuição de malware;</li><li>Spam abusivo;</li><li>Manipulação maliciosa de sistemas;</li><li>Atividades ilegais;</li><li>Coleta indevida de informações;</li><li>Tentativas de obter dados de outros usuários sem autorização;</li><li>Interferência deliberada na infraestrutura;</li><li>Burlar limitações técnicas;</li><li>Explorar erros ou falhas do sistema de maneira maliciosa.</li></ul><p>A identificação de uma vulnerabilidade deve ser comunicada à equipe responsável sempre que possível.</p>` },
            { id: 'tickets', title: '6. Sistema de tickets', content: `<p>O Zyntrax pode oferecer sistemas de atendimento por tickets.</p><p>Os administradores podem configurar categorias, permissões, mensagens e fluxos de atendimento.</p><p>O conteúdo de um ticket pode ser acessado pelos usuários e membros da equipe que possuam as permissões correspondentes dentro do Discord.</p><p>Administradores são responsáveis pela configuração das permissões de seus próprios servidores.</p>` },
            { id: 'economia', title: '7. Economia e moeda virtual', content: `<p>Algumas versões do Zyntrax podem disponibilizar sistemas de economia virtual.</p><p>Qualquer moeda virtual disponibilizada pelo sistema:</p><ul><li>Não representa dinheiro real;</li><li>Não constitui moeda oficial;</li><li>Não possui valor monetário garantido;</li><li>Não representa saldo bancário;</li><li>Não pode ser considerada investimento.</li></ul><p>O projeto pode alterar, redefinir, remover ou ajustar valores da economia virtual para manter o equilíbrio do sistema.</p>` },
            { id: 'loja', title: '8. Loja e produtos', content: `<p>Quando disponível, o Zyntrax poderá permitir que administradores configurem produtos e serviços dentro de uma loja.</p><p>Os produtos, preços, condições, validade e benefícios são definidos pelo administrador responsável pela respectiva loja, salvo quando expressamente informado pelo próprio Zyntrax.</p><p>O Zyntrax atua como ferramenta tecnológica e não necessariamente como vendedor dos produtos disponibilizados por terceiros.</p>` },
            { id: 'pagamentos', title: '9. Pagamentos', content: `<p>Quando houver suporte a pagamentos, as informações apresentadas antes da conclusão da compra devem ser verificadas pelo usuário.</p><p>O Zyntrax poderá utilizar serviços externos para processamento ou confirmação de pagamentos.</p><p>O projeto não deve ser utilizado para realizar transações fraudulentas, chargebacks abusivos ou qualquer tentativa de manipulação de pagamentos.</p>` },
            { id: 'disponibilidade', title: '10. Disponibilidade', content: `<p>Embora sejam realizados esforços para manter o Zyntrax disponível e funcional, não é possível garantir disponibilidade ininterrupta.</p><p>O serviço poderá ficar temporariamente indisponível devido a:</p><ul><li>Manutenção;</li><li>Atualizações;</li><li>Falhas técnicas;</li><li>Problemas de infraestrutura;</li><li>Problemas do Discord;</li><li>Serviços externos;</li><li>Eventos fora do controle do projeto.</li></ul>` },
            { id: 'atualizacoes', title: '11. Atualizações', content: `<p>O Zyntrax poderá receber atualizações, correções, melhorias, alterações de funcionamento ou remoção de funcionalidades.</p><p>Determinadas mudanças poderão ocorrer sem aviso prévio quando forem necessárias para segurança, estabilidade ou correção de problemas.</p>` },
            { id: 'seguranca', title: '12. Segurança', content: `<p>É proibida qualquer tentativa de comprometer a segurança do Zyntrax.</p><p>Isso inclui tentativas de:</p><ul><li>Obter acesso não autorizado;</li><li>Explorar vulnerabilidades;</li><li>Interceptar informações;</li><li>Manipular requisições;</li><li>Contornar mecanismos de segurança;</li><li>Derrubar ou prejudicar o serviço.</li></ul>` },
            { id: 'propriedade', title: '13. Propriedade intelectual', content: `<p>O Zyntrax, sua identidade visual, nome, logotipo, código, interface e demais elementos desenvolvidos pelo projeto pertencem aos respectivos titulares de direitos, salvo quando indicado de maneira diferente.</p><p>Nenhum direito de propriedade intelectual é transferido ao usuário simplesmente pela utilização do serviço.</p>` },
            { id: 'terceiros', title: '14. Serviços de terceiros', content: `<p>O funcionamento do Zyntrax pode depender de serviços externos, incluindo o Discord e outras plataformas de infraestrutura ou integração.</p><p>O funcionamento desses serviços está sujeito aos respectivos termos e políticas.</p><p>Alterações realizadas por terceiros podem afetar determinadas funcionalidades do Zyntrax.</p>` },
            { id: 'suspensao', title: '15. Suspensão e encerramento', content: `<p>O acesso a determinados recursos poderá ser limitado ou interrompido quando houver:</p><ul><li>Violação destes Termos;</li><li>Abuso do serviço;</li><li>Tentativa de comprometimento da segurança;</li><li>Uso ilícito;</li><li>Fraude;</li><li>Comportamento que prejudique deliberadamente o funcionamento do sistema.</li></ul><p>Quando apropriado, poderão ser aplicadas medidas proporcionais à situação.</p>` },
            { id: 'limitacao', title: '16. Limitação de responsabilidade', content: `<p>O Zyntrax é disponibilizado como uma ferramenta tecnológica.</p><p>Dentro dos limites permitidos pela legislação aplicável, o projeto não garante que o serviço estará livre de interrupções, erros ou indisponibilidades.</p><p>O usuário e os administradores devem avaliar adequadamente os riscos associados à utilização das ferramentas disponibilizadas.</p>` },
            { id: 'alteracoes', title: '17. Alterações destes Termos', content: `<p>Estes Termos poderão ser atualizados para refletir:</p><ul><li>Mudanças no serviço;</li><li>Novas funcionalidades;</li><li>Alterações legais;</li><li>Melhorias de segurança;</li><li>Mudanças operacionais.</li></ul><p>A versão mais recente estará sempre disponível nesta página.</p>` },
            { id: 'legislacao', title: '18. Legislação aplicável', content: `<p>Estes Termos deverão ser interpretados de acordo com a legislação aplicável à operação do serviço e aos direitos dos usuários.</p><p>Quando houver legislação específica de proteção ao consumidor, privacidade ou outros direitos aplicáveis, ela deverá ser observada nos limites correspondentes.</p>` },
            { id: 'contato', title: '19. Contato e suporte', content: `<p>Caso você tenha dúvidas relacionadas ao funcionamento do Zyntrax, aos presentes Termos ou queira comunicar um problema relacionado ao serviço, utilize os canais oficiais de suporte disponibilizados pelo projeto.</p><a href="#" class="btn-support">ABRIR CENTRAL DE SUPORTE</a>` }
        ];
        const sidebar = document.getElementById('sidebar'); const contentArea = document.getElementById('content-area');
        termsData.forEach(sec => { const link = document.createElement('a'); link.href = `#${sec.id}`; link.className = 'sidebar-link'; link.innerText = sec.title; sidebar.appendChild(link); const section = document.createElement('section'); section.id = sec.id; section.innerHTML = `<h2>${sec.title}</h2>${sec.content}`; contentArea.appendChild(section); });
        window.addEventListener('scroll', () => { let current = ''; document.querySelectorAll('section').forEach(section => { if (scrollY >= section.offsetTop - 150) current = section.getAttribute('id'); }); document.querySelectorAll('.sidebar-link').forEach(link => { link.classList.remove('active'); if (link.getAttribute('href') === `#${current}`) link.classList.add('active'); }); });
    </script>
</body>
</html>
TERMS_EOF

zip -r zyntrax-terms.zip zyntrax-terms/
mv zyntrax-terms.zip /sdcard/Download/
echo "✅ ZIP dos Termos criado e movido para Download!"
cp ~/zyntrax-terms.zip /storage/emulated/0/Download/
cd ~ && rm -rf zyntrax-privacy && mkdir -p zyntrax-privacy
# 1. Gerar o HTML completo da Política de Privacidade
cat > zyntrax-privacy/index.html << 'PRIVACY_EOF'
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Política de Privacidade | Zyntrax</title>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&family=Inter:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        :root { --bg: #050507; --surface: rgba(20, 20, 25, 0.6); --border: rgba(255, 255, 255, 0.06); --text: #cbd5e1; --accent: #10b981; }
        * { margin: 0; padding: 0; box-sizing: border-box; scroll-behavior: smooth; }
        body { font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); line-height: 1.8; }
        header { position: fixed; top: 0; width: 100%; z-index: 100; background: rgba(5, 5, 7, 0.9); backdrop-filter: blur(10px); border-bottom: 1px solid var(--border); }
        .nav-container { max-width: 1200px; margin: 0 auto; padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center; }
        .logo { font-family: 'JetBrains Mono', monospace; font-weight: 500; color: var(--accent); letter-spacing: -0.05em; }
        .main-wrapper { max-width: 900px; margin: 80px auto 0; padding: 2rem; }
        .hero-card { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 3rem 2rem; text-align: center; margin-bottom: 4rem; position: relative; overflow: hidden; }
        .hero-card::after { content: ''; position: absolute; bottom: 0; left: 0; width: 100%; height: 1px; background: linear-gradient(90deg, transparent, var(--accent), transparent); opacity: 0.5; }
        .hero-card h1 { font-size: clamp(1.8rem, 4vw, 2.5rem); color: white; margin-bottom: 1rem; font-weight: 700; }
        .flow-visual { display: flex; justify-content: center; gap: 1rem; margin: 2rem 0; font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: var(--accent); opacity: 0.9; flex-wrap: wrap; }
        .flow-step { background: rgba(16, 185, 129, 0.1); padding: 6px 12px; border-radius: 4px; border: 1px solid rgba(16, 185, 129, 0.2); }
        section { margin-bottom: 2rem; padding: 2rem; background: var(--surface); border-radius: 12px; border: 1px solid var(--border); transition: transform 0.3s ease; }
        section:hover { transform: translateY(-2px); border-color: rgba(255,255,255,0.1); }
        h2 { color: white; margin-bottom: 1.2rem; font-size: 1.3rem; display: flex; align-items: center; gap: 10px; }
        h2::before { content: ''; width: 3px; height: 20px; background: var(--accent); border-radius: 2px; }
        p, li { color: var(--text); margin-bottom: 1rem; font-size: 0.95rem; }
        ul { padding-left: 1.5rem; margin-bottom: 1.5rem; list-style: none; }
        li { position: relative; padding-left: 1.5rem; }
        li::before { content: '›'; color: var(--accent); position: absolute; left: 0; font-weight: bold; font-size: 1.2rem; line-height: 1; }
        .btn-privacy { display: inline-block; background: transparent; border: 1px solid var(--accent); color: var(--accent); padding: 12px 24px; border-radius: 8px; text-decoration: none; font-family: 'JetBrains Mono', monospace; transition: 0.3s; font-size: 0.9rem; margin-top: 1rem; }
        .btn-privacy:hover { background: rgba(16, 185, 129, 0.1); box-shadow: 0 0 20px rgba(16, 185, 129, 0.1); }
        footer { text-align: center; padding: 4rem 0; color: var(--text); opacity: 0.5; font-size: 0.8rem; border-top: 1px solid var(--border); margin-top: 4rem; }
        @media (max-width: 768px) { .main-wrapper { padding: 1.5rem; margin-top: 70px; } .hero-card { padding: 2rem 1.5rem; } .flow-visual { flex-direction: column; align-items: center; gap: 0.5rem; } .flow-step { width: 100%; text-align: center; } section { padding: 1.5rem; } h2 { font-size: 1.2rem; } .btn-privacy { width: 100%; text-align: center; } }
    </style>
</head>
<body>
    <header><div class="nav-container"><div class="logo">ZYNTRAX_PRIVACY</div><nav style="display: flex; gap: 1.5rem; font-size: 0.9rem;"><a href="../zyntrax-termos" style="color: var(--text); text-decoration: none;">Termos</a><a href="#" style="color: var(--accent); text-decoration: none; font-weight: 600;">Privacidade</a></nav></div></header>
    <div class="main-wrapper">
        <div class="hero-card">
            <h1>Política de Privacidade</h1>
            <p>Transparência sobre como o Zyntrax coleta, utiliza, armazena e protege informações relacionadas à utilização do serviço.</p>
            <div class="flow-visual"><span class="flow-step">COLETA</span><span style="align-self:center; opacity:0.5">→</span><span class="flow-step">PROCESSAMENTO</span><span style="align-self:center; opacity:0.5">→</span><span class="flow-step">ARMAZENAMENTO</span><span style="align-self:center; opacity:0.5">→</span><span class="flow-step">EXCLUSÃO</span></div>
            <span style="font-size: 0.8rem; opacity: 0.6; display:block; margin-top:1rem;">Última atualização: 05/09/2026 | v1.0</span>
        </div>
        <div id="privacy-content"></div>
        <div style="text-align: center; margin-top: 4rem; margin-bottom: 2rem;"><a href="#" class="btn-privacy">SOLICITAR SUPORTE DE PRIVACIDADE</a></div>
    </div>
    <footer>
        <p>Zyntrax | Fundado por Nix Founder</p>
        <p>© 2026 Zyntrax. Todos os direitos reservados.</p>
        <div style="margin-top: 1rem; display: flex; justify-content: center; gap: 1rem;"><a href="../zyntrax-termos" style="color: inherit; text-decoration: none;">Termos de Uso</a><a href="#" style="color: inherit; text-decoration: none;">Política de Privacidade</a><a href="#" style="color: inherit; text-decoration: none;">Suporte</a></div>
    </footer>
    <script>
        const privacyData = [
            { id: 'intro', title: '1. Introdução', content: `<p>O Zyntrax valoriza a privacidade dos usuários e busca tratar informações de maneira responsável, transparente e compatível com as finalidades para as quais são necessárias.</p><p>Esta Política explica como determinadas informações podem ser processadas quando você utiliza o Zyntrax.</p>` },
            { id: 'info-processadas', title: '2. Quais informações podem ser processadas', content: `<p>Dependendo das funcionalidades utilizadas e da configuração realizada pelo administrador do servidor, o Zyntrax poderá processar determinadas informações relacionadas ao Discord.</p><p><strong>IDENTIFICADORES DO DISCORD:</strong></p><ul><li>ID do usuário;</li><li>ID do servidor;</li><li>ID de canais;</li><li>ID de cargos;</li><li>ID de mensagens, quando necessário para determinada funcionalidade.</li></ul><p><strong>INFORMAÇÕES DE CONFIGURAÇÃO:</strong></p><p>Podem ser armazenadas informações necessárias para manter configurações do bot, como:</p><ul><li>Configurações de tickets;</li><li>Categorias;</li><li>Canais;</li><li>Preferências administrativas;</li><li>Configurações de sistemas;</li><li>Configurações de economia;</li><li>Configurações da loja.</li></ul>` },
            { id: 'utilizacao', title: '3. Informações de utilização', content: `<p>Dependendo da funcionalidade, determinados eventos podem ser processados para que o sistema consiga funcionar corretamente.</p><p>Por exemplo:</p><ul><li>Comandos utilizados;</li><li>Interações com sistemas;</li><li>Ações necessárias para executar uma funcionalidade;</li><li>Informações necessárias para prevenir abuso.</li></ul><p>O Zyntrax não deve coletar informações além do necessário para a finalidade correspondente.</p>` },
            { id: 'mensagens', title: '4. Mensagens e conteúdo', content: `<p>Algumas funcionalidades podem exigir o processamento de mensagens ou conteúdos enviados ao bot para executar determinada ação.</p><p>Quando isso ocorrer, o processamento deverá estar relacionado à finalidade específica da funcionalidade.</p><p>O conteúdo não deve ser utilizado para finalidades incompatíveis com a funcionalidade que justificou seu processamento.</p>` },
            { id: 'finalidades', title: '5. Para que as informações são utilizadas', content: `<p>As informações podem ser utilizadas para:</p><ul><li>Executar funcionalidades do Zyntrax;</li><li>Manter configurações;</li><li>Processar comandos;</li><li>Gerenciar tickets;</li><li>Administrar sistemas;</li><li>Manter sistemas de economia;</li><li>Operar funcionalidades da loja;</li><li>Prevenir abusos;</li><li>Detectar comportamentos incompatíveis com o serviço;</li><li>Corrigir erros;</li><li>Melhorar estabilidade;</li><li>Proteger a infraestrutura.</li></ul>` },
            { id: 'minimizacao', title: '6. Minimização de dados', content: `<p>O Zyntrax busca seguir o princípio de minimização de dados.</p><p>Isso significa que informações devem ser processadas somente quando houver uma necessidade relacionada ao funcionamento, segurança, manutenção ou finalidade legítima do serviço.</p><p>Não há necessidade de coletar informações pessoais apenas porque elas estão disponíveis.</p>` },
            { id: 'armazenamento', title: '7. Armazenamento', content: `<p>Quando determinadas informações precisarem ser armazenadas, elas poderão permanecer em sistemas de armazenamento utilizados pelo projeto durante o período necessário para cumprir a finalidade correspondente.</p><p>O período de armazenamento pode variar conforme:</p><ul><li>Tipo de informação;</li><li>Funcionalidade;</li><li>Necessidade operacional;</li><li>Segurança;</li><li>Obrigações legais.</li></ul>` },
            { id: 'seguranca', title: '8. Segurança', content: `<p>Medidas técnicas e administrativas podem ser utilizadas para reduzir riscos de acesso não autorizado, alteração, perda ou divulgação indevida das informações.</p><p>Nenhum sistema conectado à internet pode ser considerado absolutamente seguro.</p><p>Por isso, também é importante que administradores mantenham suas próprias contas e permissões devidamente protegidas.</p>` },
            { id: 'compartilhamento', title: '9. Compartilhamento', content: `<p>O Zyntrax não deve comercializar informações pessoais dos usuários.</p><p>Informações poderão ser processadas por fornecedores técnicos necessários para a operação do serviço, quando aplicável.</p><p>Também poderá haver compartilhamento ou divulgação quando isso for necessário para:</p><ul><li>Cumprimento de obrigação legal;</li><li>Proteção de direitos;</li><li>Investigação de abuso;</li><li>Segurança;</li><li>Cumprimento de determinações válidas das autoridades competentes.</li></ul>` },
            { id: 'discord', title: '10. Discord', content: `<p>O Zyntrax funciona integrado à plataforma Discord.</p><p>Por isso, determinadas informações são disponibilizadas pela própria plataforma para permitir que bots e aplicativos funcionem.</p><p>A utilização do Discord também está sujeita às políticas e termos da própria plataforma.</p><p>O Zyntrax não controla as práticas de privacidade do Discord.</p>` },
            { id: 'administradores', title: '11. Administradores de servidores', content: `<p>Administradores possuem controle sobre a configuração do Zyntrax em seus servidores.</p><p>Eles podem determinar:</p><ul><li>Quais sistemas estarão ativos;</li><li>Quais canais serão utilizados;</li><li>Quais membros terão determinadas permissões;</li><li>Como os tickets funcionarão;</li><li>Quais recursos estarão disponíveis.</li></ul><p>Administradores devem configurar essas funcionalidades de maneira responsável.</p>` },
            { id: 'loja-pagamentos', title: '12. Loja e pagamentos', content: `<p>Quando funcionalidades comerciais estiverem disponíveis, determinados dados relacionados à operação de uma compra poderão ser processados para permitir:</p><ul><li>Identificação da transação;</li><li>Confirmação do pagamento;</li><li>Entrega do produto;</li><li>Prevenção de fraude;</li><li>Registro necessário da operação.</li></ul><p>Dados de pagamento sensíveis não devem ser armazenados pelo Zyntrax quando não forem necessários para a finalidade da operação.</p><p>Quando um pagamento depender de um provedor externo, o processamento também estará sujeito às políticas desse provedor.</p>` },
            { id: 'moeda-virtual', title: '13. Moeda virtual', content: `<p>Sistemas de economia virtual podem armazenar informações necessárias para manter o saldo e o funcionamento da economia de determinado servidor.</p><p>Esses dados existem para permitir que o sistema execute funcionalidades como:</p><ul><li>Saldo;</li><li>Recompensas;</li><li>Compras;</li><li>Histórico necessário;</li><li>Transações internas.</li></ul><p>A moeda virtual não representa dinheiro real.</p>` },
            { id: 'retencao', title: '14. Retenção de dados', content: `<p>As informações poderão ser mantidas enquanto forem necessárias para:</p><ul><li>Funcionamento do serviço;</li><li>Manutenção das configurações;</li><li>Segurança;</li><li>Prevenção de abusos;</li><li>Cumprimento de obrigações legais;</li><li>Resolução de disputas.</li></ul><p>Quando deixarem de ser necessárias, poderão ser eliminadas, anonimizadas ou mantidas somente quando houver fundamento legítimo para sua conservação.</p>` },
            { id: 'exclusao', title: '15. Exclusão de informações', content: `<p>Quando aplicável, o usuário poderá solicitar a exclusão de informações relacionadas à sua utilização do Zyntrax.</p><p>A solicitação poderá estar sujeita à verificação para evitar que terceiros solicitem a exclusão de informações pertencentes a outra pessoa.</p><p>Algumas informações poderão precisar ser mantidas quando houver obrigação legal ou outra justificativa legítima.</p>` },
            { id: 'direitos', title: '16. Direitos dos usuários', content: `<p>Dependendo da legislação aplicável, o usuário poderá possuir direitos relacionados aos seus dados, incluindo:</p><ul><li>Confirmação da existência de tratamento;</li><li>Acesso;</li><li>Correção;</li><li>Atualização;</li><li>Exclusão, quando aplicável;</li><li>Informações sobre utilização;</li><li>Revogação de determinados consentimentos, quando aplicável;</li><li>Outros direitos previstos pela legislação.</li></ul><p>Solicitações serão analisadas conforme o caso e a legislação aplicável.</p>` },
            { id: 'criancas', title: '17. Crianças e adolescentes', content: `<p>O Zyntrax reconhece que serviços utilizados em comunidades online podem envolver usuários de diferentes idades.</p><p>O serviço não deve ser utilizado para coletar deliberadamente informações pessoais de crianças ou adolescentes de maneira incompatível com a legislação aplicável.</p><p>Quando houver tratamento de dados envolvendo menores de idade, deverão ser observadas as proteções previstas na legislação correspondente.</p>` },
            { id: 'cookies', title: '18. Cookies e tecnologias semelhantes', content: `<p>Os sites oficiais do Zyntrax poderão utilizar tecnologias técnicas necessárias para funcionamento, segurança, desempenho ou análise, quando aplicável.</p><p>Caso sejam utilizados cookies não essenciais ou tecnologias semelhantes que exijam informação ou consentimento específico, isso deverá ser apresentado de maneira apropriada ao usuário.</p>` },
            { id: 'servicos-externos', title: '19. Serviços externos', content: `<p>O Zyntrax pode depender de serviços externos para hospedagem, armazenamento, processamento, autenticação, pagamentos ou outras funções técnicas.</p><p>Esses fornecedores poderão processar informações estritamente necessárias para prestar os serviços correspondentes.</p>` },
            { id: 'alteracoes', title: '20. Alterações desta Política', content: `<p>Esta Política poderá ser atualizada quando houver:</p><ul><li>Mudanças no Zyntrax;</li><li>Novas funcionalidades;</li><li>Alterações na forma de tratamento de informações;</li><li>Melhorias de segurança;</li><li>Alterações legais.</li></ul><p>A data de atualização será modificada sempre que uma nova versão relevante for publicada.</p>` },
            { id: 'transparencia', title: '21. Transparência', content: `<p>Nosso objetivo é evitar políticas excessivamente técnicas ou obscuras.</p><p>Sempre que possível, as informações devem ser apresentadas de maneira clara para que o usuário compreenda:</p><p>O que pode ser processado → Por que pode ser processado → Como pode ser utilizado → Quais opções possui.</p>` },
            { id: 'contato', title: '22. Contato', content: `<p>Para dúvidas relacionadas à privacidade, proteção de dados ou solicitações relacionadas às informações processadas pelo Zyntrax, utilize os canais oficiais disponibilizados pelo projeto.</p><a href="#" class="btn-privacy">SOLICITAR SUPORTE DE PRIVACIDADE</a>` }
        ];
        const container = document.getElementById('privacy-content');
        privacyData.forEach(sec => { const div = document.createElement('section'); div.id = sec.id; div.innerHTML = `<h2>${sec.title}</h2>${sec.content}`; container.appendChild(div); });
    </script>
</body>
</html>
PRIVACY_EOF

# 2. Compactar o site de Privacidade
zip -r zyntrax-privacy.zip zyntrax-privacy/
# 3. Copiar AMBOS os ZIPs para a pasta Download física do Android
cp ~/zyntrax-terms.zip /storage/emulated/0/Download/
cp ~/zyntrax-privacy.zip /storage/emulated/0/Download/
echo "✅ SUCESSO! Ambos os ZIPs foram copiados para /storage/emulated/0/Download/"
ls -lh /storage/emulated/0/Download/zyntrax-*.zip
cp ~/zyntrax-terms.zip ~/storage/shared/Download/
cp ~/zyntrax-privacy.zip ~/storage/shared/Download/
echo "✅ Arquivos copiados!"
ls ~/storage/shared/Download/zyntrax-*.zip
cd ~ && rm -rf zyntrax-terms && mkdir -p zyntrax-terms
cat > zyntrax-terms/index.html << 'TERMS_EOF'
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Termos de Uso | Zyntrax</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root { --bg: #0a0a0f; --surface: rgba(255, 255, 255, 0.03); --border: rgba(255, 255, 255, 0.08); --text: #e2e8f0; --text-muted: #94a3b8; --accent: #6366f1; }
        * { margin: 0; padding: 0; box-sizing: border-box; scroll-behavior: smooth; }
        body { font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); line-height: 1.7; overflow-x: hidden; }
        header { position: fixed; top: 0; width: 100%; z-index: 100; background: rgba(10, 10, 15, 0.85); backdrop-filter: blur(16px); border-bottom: 1px solid var(--border); }
        .nav-container { max-width: 1200px; margin: 0 auto; padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center; }
        .logo { font-weight: 700; font-size: 1.25rem; letter-spacing: -0.02em; color: white; }
        .version-badge { background: var(--surface); border: 1px solid var(--border); padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; color: var(--accent); font-weight: 600; }
        .main-wrapper { max-width: 1200px; margin: 80px auto 0; display: grid; grid-template-columns: 280px 1fr; gap: 4rem; padding: 2rem; min-height: calc(100vh - 200px); }
        aside { position: sticky; top: 100px; height: calc(100vh - 120px); overflow-y: auto; scrollbar-width: thin; scrollbar-color: var(--border) transparent; }
        .sidebar-link { display: block; padding: 8px 0; color: var(--text-muted); text-decoration: none; font-size: 0.9rem; border-left: 2px solid transparent; padding-left: 1rem; transition: all 0.3s ease; margin-bottom: 4px; }
        .sidebar-link:hover, .sidebar-link.active { color: white; border-left-color: var(--accent); background: linear-gradient(90deg, rgba(99, 102, 241, 0.1), transparent); }
        main { min-width: 0; }
        h1 { font-size: clamp(2rem, 5vw, 3.5rem); font-weight: 800; margin-bottom: 1rem; background: linear-gradient(to right, #fff, #94a3b8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; line-height: 1.2; }
        .hero-sub { font-size: 1.1rem; color: var(--text-muted); margin-bottom: 2rem; max-width: 600px; }
        .last-update { display: inline-block; background: var(--surface); padding: 6px 12px; border-radius: 6px; font-size: 0.8rem; color: var(--text-muted); margin-bottom: 3rem; border: 1px solid var(--border); }
        .acceptance-card { background: linear-gradient(145deg, rgba(99, 102, 241, 0.08), rgba(255,255,255,0.02)); border: 1px solid rgba(99, 102, 241, 0.3); padding: 2rem; border-radius: 16px; margin-bottom: 4rem; }
        section { margin-bottom: 4rem; scroll-margin-top: 100px; animation: fadeIn 0.5s ease; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        h2 { font-size: 1.5rem; margin-bottom: 1.5rem; color: white; border-bottom: 1px solid var(--border); padding-bottom: 0.75rem; display: flex; align-items: center; gap: 10px; }
        h2::before { content: ''; width: 4px; height: 24px; background: var(--accent); border-radius: 2px; }
        p, li { color: var(--text-muted); margin-bottom: 1rem; font-size: 1rem; }
        ul { padding-left: 1.5rem; margin-bottom: 1.5rem; list-style-type: none; }
        li { position: relative; padding-left: 1.5rem; }
        li::before { content: '•'; color: var(--accent); position: absolute; left: 0; font-weight: bold; }
        .btn-support { display: inline-flex; align-items: center; gap: 8px; background: var(--accent); color: white; padding: 14px 28px; border-radius: 8px; text-decoration: none; font-weight: 600; transition: all 0.3s; margin-top: 1rem; border: 1px solid rgba(255,255,255,0.1); }
        .btn-support:hover { transform: translateY(-2px); box-shadow: 0 10px 30px -10px rgba(99, 102, 241, 0.3); background: #4f46e5; }
        footer { border-top: 1px solid var(--border); padding: 4rem 2rem; text-align: center; color: var(--text-muted); font-size: 0.9rem; margin-top: 4rem; background: rgba(0,0,0,0.2); }
        footer h3 { color: white; margin-bottom: 0.5rem; font-size: 1.2rem; }
        .footer-links { margin-top: 1.5rem; display: flex; justify-content: center; gap: 1.5rem; flex-wrap: wrap; }
        .footer-links a { color: var(--text-muted); text-decoration: none; transition: 0.3s; font-size: 0.85rem; }
        .footer-links a:hover { color: var(--accent); }
        @media (max-width: 900px) { .main-wrapper { grid-template-columns: 1fr; gap: 2rem; padding: 1.5rem; margin-top: 70px; } aside { display: none; } h1 { font-size: 2.2rem; } .acceptance-card { padding: 1.5rem; } .nav-container { padding: 1rem 1.5rem; } }
        @media (max-width: 480px) { h1 { font-size: 1.8rem; } h2 { font-size: 1.3rem; } p, li { font-size: 0.95rem; } .btn-support { width: 100%; justify-content: center; } }
    </style>
</head>
<body>
    <header><div class="nav-container"><div class="logo">ZYNTRAX</div><span class="version-badge">v1.0</span></div></header>
    <div class="main-wrapper">
        <aside id="sidebar"></aside>
        <main>
            <h1>Termos de Uso</h1>
            <p class="hero-sub">As regras que estabelecem como o Zyntrax pode ser utilizado de forma segura, responsável e transparente.</p>
            <span class="last-update">Última atualização: 05 de setembro de 2026</span>
            <div class="acceptance-card"><h3>Aceitação dos Termos</h3><p style="margin-top: 10px;">Ao utilizar, adicionar ou interagir com o Zyntrax, você declara que leu e compreendeu estes Termos de Uso e concorda em respeitá-los integralmente.</p></div>
            <div id="content-area"></div>
        </main>
    </div>
    <footer>
        <h3>ZYNTRAX</h3>
        <p>Sistema de automação e gerenciamento para comunidades Discord.</p>
        <p>Fundado por Nix Founder</p>
        <p style="margin-top: 1rem; opacity: 0.7;">© 2026 Zyntrax. Todos os direitos reservados.</p>
        <div class="footer-links"><a href="#">Termos de Uso</a><a href="../zyntrax-privacidade">Política de Privacidade</a><a href="#">Suporte</a></div>
    </footer>
    <script>
        const termsData = [
            { id: 'sobre', title: '1. Sobre o Zyntrax', content: `<p>O Zyntrax é uma solução desenvolvida para auxiliar na administração, organização, atendimento e automação de comunidades hospedadas na plataforma Discord.</p><p>Dependendo da configuração realizada pelos administradores, o Zyntrax pode disponibilizar recursos como:</p><ul><li>Sistema de tickets;</li><li>Atendimento e suporte;</li><li>Moderação;</li><li>Automação;</li><li>Sistemas de economia virtual;</li><li>Loja;</li><li>Gerenciamento de produtos;</li><li>Sistemas de recompensas;</li><li>Integrações;</li><li>Recursos administrativos;</li><li>Ferramentas de organização de servidores;</li><li>Outros recursos disponibilizados pelo projeto.</li></ul><p>Os recursos disponíveis podem variar de acordo com a versão do Zyntrax, configuração do servidor e atualizações realizadas pelo projeto.</p>` },
            { id: 'aceitacao', title: '2. Aceitação dos Termos', content: `<p>Ao utilizar o Zyntrax, você concorda com estes Termos de Uso.</p><p>Caso não concorde com qualquer parte deste documento, deverá interromper a utilização do serviço.</p><p>O administrador de um servidor também é responsável por garantir que a utilização do Zyntrax dentro de sua comunidade esteja de acordo com estes Termos.</p><p>A utilização contínua do serviço após alterações nos Termos poderá representar a aceitação da versão atualizada.</p>` },
            { id: 'requisitos', title: '3. Requisitos de utilização', content: `<p>Para utilizar determinadas funcionalidades do Zyntrax, pode ser necessário possuir uma conta válida no Discord e ter as permissões necessárias dentro do servidor.</p><p>O usuário deve:</p><ul><li>Utilizar o serviço de maneira legítima;</li><li>Respeitar as regras do Discord;</li><li>Respeitar as regras do servidor em que o Zyntrax está instalado;</li><li>Não tentar explorar falhas;</li><li>Não tentar obter acesso não autorizado;</li><li>Não utilizar o serviço para atividades ilícitas;</li><li>Não interferir deliberadamente no funcionamento do sistema.</li></ul>` },
            { id: 'responsabilidade', title: '4. Responsabilidade do usuário', content: `<p>Cada usuário é responsável pelas ações realizadas utilizando sua conta Discord e pelas interações realizadas com o Zyntrax.</p><p>O Zyntrax não se responsabiliza por decisões tomadas por administradores de servidores utilizando as ferramentas disponibilizadas pelo sistema.</p><p>Administradores são responsáveis por configurar adequadamente os recursos e verificar as permissões concedidas ao bot.</p>` },
            { id: 'proibido', title: '5. Uso proibido', content: `<p>É proibido utilizar o Zyntrax para:</p><ul><li>Fraudes;</li><li>Golpes;</li><li>Tentativas de invasão;</li><li>Exploração de vulnerabilidades;</li><li>Distribuição de malware;</li><li>Spam abusivo;</li><li>Manipulação maliciosa de sistemas;</li><li>Atividades ilegais;</li><li>Coleta indevida de informações;</li><li>Tentativas de obter dados de outros usuários sem autorização;</li><li>Interferência deliberada na infraestrutura;</li><li>Burlar limitações técnicas;</li><li>Explorar erros ou falhas do sistema de maneira maliciosa.</li></ul><p>A identificação de uma vulnerabilidade deve ser comunicada à equipe responsável sempre que possível.</p>` },
            { id: 'tickets', title: '6. Sistema de tickets', content: `<p>O Zyntrax pode oferecer sistemas de atendimento por tickets.</p><p>Os administradores podem configurar categorias, permissões, mensagens e fluxos de atendimento.</p><p>O conteúdo de um ticket pode ser acessado pelos usuários e membros da equipe que possuam as permissões correspondentes dentro do Discord.</p><p>Administradores são responsáveis pela configuração das permissões de seus próprios servidores.</p>` },
            { id: 'economia', title: '7. Economia e moeda virtual', content: `<p>Algumas versões do Zyntrax podem disponibilizar sistemas de economia virtual.</p><p>Qualquer moeda virtual disponibilizada pelo sistema:</p><ul><li>Não representa dinheiro real;</li><li>Não constitui moeda oficial;</li><li>Não possui valor monetário garantido;</li><li>Não representa saldo bancário;</li><li>Não pode ser considerada investimento.</li></ul><p>O projeto pode alterar, redefinir, remover ou ajustar valores da economia virtual para manter o equilíbrio do sistema.</p>` },
            { id: 'loja', title: '8. Loja e produtos', content: `<p>Quando disponível, o Zyntrax poderá permitir que administradores configurem produtos e serviços dentro de uma loja.</p><p>Os produtos, preços, condições, validade e benefícios são definidos pelo administrador responsável pela respectiva loja, salvo quando expressamente informado pelo próprio Zyntrax.</p><p>O Zyntrax atua como ferramenta tecnológica e não necessariamente como vendedor dos produtos disponibilizados por terceiros.</p>` },
            { id: 'pagamentos', title: '9. Pagamentos', content: `<p>Quando houver suporte a pagamentos, as informações apresentadas antes da conclusão da compra devem ser verificadas pelo usuário.</p><p>O Zyntrax poderá utilizar serviços externos para processamento ou confirmação de pagamentos.</p><p>O projeto não deve ser utilizado para realizar transações fraudulentas, chargebacks abusivos ou qualquer tentativa de manipulação de pagamentos.</p>` },
            { id: 'disponibilidade', title: '10. Disponibilidade', content: `<p>Embora sejam realizados esforços para manter o Zyntrax disponível e funcional, não é possível garantir disponibilidade ininterrupta.</p><p>O serviço poderá ficar temporariamente indisponível devido a:</p><ul><li>Manutenção;</li><li>Atualizações;</li><li>Falhas técnicas;</li><li>Problemas de infraestrutura;</li><li>Problemas do Discord;</li><li>Serviços externos;</li><li>Eventos fora do controle do projeto.</li></ul>` },
            { id: 'atualizacoes', title: '11. Atualizações', content: `<p>O Zyntrax poderá receber atualizações, correções, melhorias, alterações de funcionamento ou remoção de funcionalidades.</p><p>Determinadas mudanças poderão ocorrer sem aviso prévio quando forem necessárias para segurança, estabilidade ou correção de problemas.</p>` },
            { id: 'seguranca', title: '12. Segurança', content: `<p>É proibida qualquer tentativa de comprometer a segurança do Zyntrax.</p><p>Isso inclui tentativas de:</p><ul><li>Obter acesso não autorizado;</li><li>Explorar vulnerabilidades;</li><li>Interceptar informações;</li><li>Manipular requisições;</li><li>Contornar mecanismos de segurança;</li><li>Derrubar ou prejudicar o serviço.</li></ul>` },
            { id: 'propriedade', title: '13. Propriedade intelectual', content: `<p>O Zyntrax, sua identidade visual, nome, logotipo, código, interface e demais elementos desenvolvidos pelo projeto pertencem aos respectivos titulares de direitos, salvo quando indicado de maneira diferente.</p><p>Nenhum direito de propriedade intelectual é transferido ao usuário simplesmente pela utilização do serviço.</p>` },
            { id: 'terceiros', title: '14. Serviços de terceiros', content: `<p>O funcionamento do Zyntrax pode depender de serviços externos, incluindo o Discord e outras plataformas de infraestrutura ou integração.</p><p>O funcionamento desses serviços está sujeito aos respectivos termos e políticas.</p><p>Alterações realizadas por terceiros podem afetar determinadas funcionalidades do Zyntrax.</p>` },
            { id: 'suspensao', title: '15. Suspensão e encerramento', content: `<p>O acesso a determinados recursos poderá ser limitado ou interrompido quando houver:</p><ul><li>Violação destes Termos;</li><li>Abuso do serviço;</li><li>Tentativa de comprometimento da segurança;</li><li>Uso ilícito;</li><li>Fraude;</li><li>Comportamento que prejudique deliberadamente o funcionamento do sistema.</li></ul><p>Quando apropriado, poderão ser aplicadas medidas proporcionais à situação.</p>` },
            { id: 'limitacao', title: '16. Limitação de responsabilidade', content: `<p>O Zyntrax é disponibilizado como uma ferramenta tecnológica.</p><p>Dentro dos limites permitidos pela legislação aplicável, o projeto não garante que o serviço estará livre de interrupções, erros ou indisponibilidades.</p><p>O usuário e os administradores devem avaliar adequadamente os riscos associados à utilização das ferramentas disponibilizadas.</p>` },
            { id: 'alteracoes', title: '17. Alterações destes Termos', content: `<p>Estes Termos poderão ser atualizados para refletir:</p><ul><li>Mudanças no serviço;</li><li>Novas funcionalidades;</li><li>Alterações legais;</li><li>Melhorias de segurança;</li><li>Mudanças operacionais.</li></ul><p>A versão mais recente estará sempre disponível nesta página.</p>` },
            { id: 'legislacao', title: '18. Legislação aplicável', content: `<p>Estes Termos deverão ser interpretados de acordo com a legislação aplicável à operação do serviço e aos direitos dos usuários.</p><p>Quando houver legislação específica de proteção ao consumidor, privacidade ou outros direitos aplicáveis, ela deverá ser observada nos limites correspondentes.</p>` },
            { id: 'contato', title: '19. Contato e suporte', content: `<p>Caso você tenha dúvidas relacionadas ao funcionamento do Zyntrax, aos presentes Termos ou queira comunicar um problema relacionado ao serviço, utilize os canais oficiais de suporte disponibilizados pelo projeto.</p><a href="#" class="btn-support">ABRIR CENTRAL DE SUPORTE</a>` }
        ];
        const sidebar = document.getElementById('sidebar'); const contentArea = document.getElementById('content-area');
        termsData.forEach(sec => { const link = document.createElement('a'); link.href = `#${sec.id}`; link.className = 'sidebar-link'; link.innerText = sec.title; sidebar.appendChild(link); const section = document.createElement('section'); section.id = sec.id; section.innerHTML = `<h2>${sec.title}</h2>${sec.content}`; contentArea.appendChild(section); });
        window.addEventListener('scroll', () => { let current = ''; document.querySelectorAll('section').forEach(section => { if (scrollY >= section.offsetTop - 150) current = section.getAttribute('id'); }); document.querySelectorAll('.sidebar-link').forEach(link => { link.classList.remove('active'); if (link.getAttribute('href') === `#${current}`) link.classList.add('active'); }); });
    </script>
</body>
</html>
TERMS_EOF

# Compactar e copiar para a Download
zip -r zyntrax-terms.zip zyntrax-terms/
cp ~/zyntrax-terms.zip ~/storage/shared/Download/
echo "✅ ZIP dos Termos gerado e copiado para a Download!"
ls -lh ~/storage/shared/Download/zyntrax-*.zip
cd ~ && rm -rf zyntrax-bot && mkdir -p zyntrax-bot
# 1. Criar .gitignore e .env.example (Token NUNCA será enviado)
cat > zyntrax-bot/.gitignore << 'EOF'
node_modules/
.env
*.log
.DS_Store
EOF

cat > zyntrax-bot/.env.example << 'EOF'
DISCORD_TOKEN=seu_token_aqui
CLIENT_ID=seu_client_id_aqui
GUILD_ID=sua_guild_id_aqui
EOF

# 2. Criar package.json otimizado para Discloud
cat > zyntrax-bot/package.json << 'EOF'
{
  "name": "zyntrax-bot",
  "version": "1.0.0",
  "description": "Bot Zyntrax para Discord",
  "main": "index.js",
  "scripts": {
    "start": "node index.js"
  },
  "dependencies": {
    "discord.js": "^14.14.1",
    "dotenv": "^16.3.1"
  },
  "engines": {
    "node": ">=18.0.0"
  }
}
EOF

# 3. Criar index.js seguro (lê variáveis da Discloud)
cat > zyntrax-bot/index.js << 'BOT_EOF'
require('dotenv').config();
const { Client, GatewayIntentBits } = require('discord.js');

// Validação de segurança: impede inicialização sem token
if (!process.env.DISCORD_TOKEN) {
    console.error(' ERRO CRÍTICO: DISCORD_TOKEN não configurado nas variáveis de ambiente!');
    process.exit(1);
}

const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent
    ]
});

client.once('ready', () => {
    console.log(`✅ Zyntrax Bot online como ${client.user.tag}`);
});

client.on('messageCreate', async (message) => {
    if (message.author.bot) return;
    
    if (message.content === '!ping') {
        await message.reply('🏓 Pong! Latência: ' + Date.now() - message.createdTimestamp + 'ms');
    }
});

client.login(process.env.DISCORD_TOKEN);
BOT_EOF

# 4. Compactar e copiar para Download
zip -r zyntrax-bot.zip zyntrax-bot/
cp ~/zyntrax-bot.zip ~/storage/shared/Download/
echo "✅ ZIP do BOT gerado e copiado para Download!"
ls -lh ~/storage/shared/Download/zyntrax-*.zip
cd ~/zyntrax-bot
nano .env.local
nano.env
cd ~/zyntrax-bot && rm -rf node_modules package-lock.json
# Atualize o package.json com versão otimizada
cat > package.json << 'EOF'
{
  "name": "zyntrax-bot",
  "version": "1.0.0",
  "main": "index.js",
  "scripts": {
    "start": "node index.js"
  },
  "dependencies": {
    "discord.js": "^14.14.1"
  },
  "engines": {
    "node": ">=18.0.0"
  }
}
EOF

# Recrie o ZIP sem dotenv e node_modules
zip -r ../zyntrax-bot-optimized.zip . 
cp ../zyntrax-bot-optimized.zip ~/storage/shared/Download/
echo "✅ Novo ZIP otimizado criado!"
cat > index.js << 'BOT_EOF'
const { Client, GatewayIntentBits } = require('discord.js');

// Validação de segurança
if (!process.env.DISCORD_TOKEN) {
    console.error('ERRO: DISCORD_TOKEN não configurado!');
    process.exit(1);
}

const client = new Client({
    intents: [
        GatewayIntentBits.Guilds, // Apenas Guilds é obrigatório para comandos básicos
        GatewayIntentBits.GuildMessages // Necessário apenas se usar !ping em chats
    ]
});

client.once('ready', () => {
    console.log(`Zyntrax Online: ${client.user.tag}`);
});

client.on('messageCreate', async (msg) => {
    if (msg.author.bot || msg.content !== '!ping') return;
    await msg.reply('Pong!');
});

// Previne crash por erro não tratado
process.on('unhandledRejection', err => console.error(err));

client.login(process.env.DISCORD_TOKEN);
BOT_EOF

# Atualize o ZIP novamente
zip -r ../zyntrax-bot-optimized.zip . 
cp ../zyntrax-bot-optimized.zip ~/storage/shared/Download/
ls -la ~/zyntrax-bot/
cat ~/zyntrax-bot/console.log
ls -la ~/zyntrax-bot/*.py
cat ~/zyntrax-bot/cogs/seu-comando.py
cat ~/zyntrax-bot/index.js
cat ~/zyntrax-bot/package.json
cat ~/zyntrax-bot/.env.local
ps aux | grep node
cat ~/zyntrax-bot/.env
ls -la ~/zyntrax-bot/ | grep .env
cat ~/zyntrax-bot/.env.example
nano ~/zyntrax-bot/.env
nano .env.example
cd ~ && zip -r zyntrax-bot-completo.zip zyntrax-bot-novo/ -x "zyntrax-bot-novo/.env" "zyntrax-bot-novo/node_modules/*" "zyntrax-bot-novo/.DS_Store" && echo "✓ Arquivo zipado!"
cd ~ && zip -r zyntrax-bot-completo.zip zyntrax-bot-novo/ -x "zyntrax-bot-novo/.env" "zyntrax-bot-novo/node_modules/*"
ls -la ~/ | grep bot
cd ~ && zip -r zyntrax-bot-completo.zip zyntrax-bot/ -x "zyntrax-bot/.env" "zyntrax-bot/node_modules/*"
cp ~/zyntrax-bot-completo.zip ~/storage/shared/Download/
ls -lh ~/storage/shared/Download/zyntrax-bot-completo.zip
cd ~ && rm -f zyntrax-bot-completo.zip && zip -r zyntrax-bot-completo.zip zyntrax-bot/ -x "zyntrax-bot/.env" "zyntrax-bot/node_modules/*" "zyntrax-bot/.DS_Store" && echo "✓ ZIP criado!"
cp ~/zyntrax-bot-completo.zip ~/storage/shared/Download/ && echo "✓ Pronto em Downloads!"
ls -lh ~/storage/shared/Download/zyntrax-bot-completo.zip
cd ~/zyntrax-bot
python3 bot.py
cd ~/zyntrax-bot
python3 bot.py
ls -la ~/zyntrax-bot/
cd ~/zyntrax-bot && npm install
npm start
nank.
nano .env
nano.env.example
nano .env.example
