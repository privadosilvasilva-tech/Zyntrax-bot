import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseKey) {
  throw new Error('Variáveis Supabase não configuradas')
}

export const supabase = createClient(supabaseUrl, supabaseKey)

// Funções de helper

export async function getMessages() {
  const { data, error } = await supabase
    .from('chat_messages')
    .select('*')
    .order('timestamp', { ascending: true })
    .limit(50)

  if (error) throw error
  return data || []
}

export async function addMessage(userId, username, avatar, content) {
  const { data, error } = await supabase
    .from('chat_messages')
    .insert([
      {
        user_id: userId,
        username,
        avatar_url: avatar,
        content,
        timestamp: new Date().toISOString(),
      },
    ])
    .select()

  if (error) throw error
  return data?.[0]
}

export async function getUserTags(userId) {
  const { data, error } = await supabase
    .from('user_tags')
    .select('*')
    .eq('user_id', userId)

  if (error) throw error
  return data || []
}

export async function getTickets(userId) {
  const { data, error } = await supabase
    .from('tickets')
    .select('*')
    .eq('user_id', userId)
    .order('created_at', { ascending: false })

  if (error) throw error
  return data || []
}

export async function createTicket(userId, title, category, description, priority = 'normal') {
  const { data, error } = await supabase
    .from('tickets')
    .insert([
      {
        user_id: userId,
        title,
        category,
        description,
        priority,
        status: 'open',
      },
    ])
    .select()

  if (error) throw error
  return data?.[0]
}
