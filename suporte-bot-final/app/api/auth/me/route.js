export const dynamic = 'force-dynamic'

export async function GET(request) {
  const cookies = request.headers.get('cookie') || ''
  const sessionMatch = cookies.match(/discord_session=([^;]+)/)
  const token = sessionMatch?.[1]

  if (!token) {
    return new Response(JSON.stringify({ error: 'Não autenticado' }), { status: 401, headers: { 'Content-Type': 'application/json' } })
  }

  try {
    const response = await fetch('https://discord.com/api/users/@me', {
      headers: { Authorization: `Bearer ${token}` },
    })

    if (!response.ok) {
      throw new Error('Token inválido')
    }

    const user = await response.json()

    return new Response(
      JSON.stringify({
        id: user.id,
        username: user.username,
        discriminator: user.discriminator,
        email: user.email,
        avatar: user.avatar ? `https://cdn.discordapp.com/avatars/${user.id}/${user.avatar}.png` : null,
      }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    )
  } catch (error) {
    console.error('Erro ao buscar usuário:', error)
    return new Response(JSON.stringify({ error: 'Erro ao buscar dados' }), { status: 500, headers: { 'Content-Type': 'application/json' } })
  }
}
