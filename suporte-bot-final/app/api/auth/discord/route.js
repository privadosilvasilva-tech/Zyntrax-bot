import { redirect } from 'next/navigation'

export async function GET() {
  const clientId = process.env.DISCORD_CLIENT_ID
  const redirectUri = process.env.DISCORD_REDIRECT_URI

  if (!clientId || !redirectUri) {
    return new Response('Configuração de Discord incompleta', { status: 500 })
  }

  const authUrl = new URL('https://discord.com/api/oauth2/authorize')
  authUrl.searchParams.append('client_id', clientId)
  authUrl.searchParams.append('redirect_uri', redirectUri)
  authParams.searchParams.append('response_type', 'code')
  authUrl.searchParams.append('scope', 'identify email')

  redirect(authUrl.toString())
}
