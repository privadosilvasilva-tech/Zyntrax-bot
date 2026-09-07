import '../styles/globals.css'

export const metadata = {
  title: 'Suporte Bot - Chat ao Vivo',
  description: 'Sistema de suporte completo integrado ao Discord',
  icons: {
    icon: '🤖',
  },
}

export default function RootLayout({ children }) {
  return (
    <html lang="pt-BR">
      <head>
        <meta name="theme-color" content="#0a0a0f" />
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=5" />
      </head>
      <body>{children}</body>
    </html>
  )
}
