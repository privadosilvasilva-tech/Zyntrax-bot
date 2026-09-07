import { redirect } from 'next/navigation'

export async function GET() {
  const response = redirect('/')
  response.headers.set('Set-Cookie', 'discord_session=; Path=/; HttpOnly; Max-Age=0')
  return response
}
