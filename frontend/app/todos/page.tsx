import { createClient } from '@/utils/supabase/server'
import { cookies } from 'next/headers'

export default async function Page() {
  const cookieStore = await cookies()
  const supabase = createClient(cookieStore)

  const { data: todos } = await supabase.from('todos').select()

  return (
    <div className="max-w-4xl mx-auto px-4 py-10">
      <h1 className="text-2xl font-bold text-slate-800 mb-6">Supabase Todos Test Page</h1>
      <ul className="space-y-2">
        {todos && todos.length > 0 ? (
          todos.map((todo: any) => (
            <li key={todo.id} className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm text-slate-700 font-semibold">
              {todo.name}
            </li>
          ))
        ) : (
          <li className="text-slate-500 italic">No todos found or unable to fetch todos table.</li>
        )}
      </ul>
    </div>
  )
}
