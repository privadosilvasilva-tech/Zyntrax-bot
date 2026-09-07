import { redirect } from 'next/navigation'

export const dynamic = 'force-dynamic'

export async function GET(request) {
  const searchParams = request.nextUrl.searchParams
  const code = searchParams.get('code')
  const state = searchParams.get('state')

  if (!code) {
    return new Response('Erro: código não fornecido', { status: 400 })
  }

  try {
    // Trocar código por token
    const tokenResponse = await fetch('https://discord.com/api/oauth2/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        client_id: process.env.DISCORD_CLIENT_ID,
        client_secret: process.env.DISCORD_CLIENT_SECRET,
        code,
        grant_type: 'authorization_code',
        redirect_uri: process.env.DISCORD_REDIRECT_URI,
        scope: 'identify email',
      }),
    })

    const tokenData = await tokenResponse.json()

    if (!tokenData.access_token) {
      throw new Error('Falha ao obter token')
    }

    // Buscar informações do usuário
    const userResponse = await fetch('https://discord.com/api/users/@me', {
      headers: { Authorization: `Bearer ${tokenData.access_token}` },
    })

    const userData = await userResponse.json()

    // Salvar session
    const sessionCookie = `discord_session=${tokenData.access_token}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=604800`

    const response = redirect('/')
    response.headers.set('Set-Cookie', sessionCookie)

    return response
  } catch (error) {
    console.error('Erro na autenticação:', error)
    return redirect('/?error=auth_failed')
  }
}
