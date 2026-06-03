const getBackendUrl = (): string => {
  return process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:10000';
};

const getHeaders = async (): Promise<Record<string, string>> => {
  const headers: Record<string, string> = {};
  
  try {
    const { supabase, isMockAuth } = await import('./supabase');
    if (isMockAuth) {
      headers['Authorization'] = 'Bearer mock-developer-jwt-token';
    } else {
      const { data } = await supabase.auth.getSession();
      if (data?.session?.access_token) {
        headers['Authorization'] = `Bearer ${data.session.access_token}`;
      }
    }
  } catch (e) {
    console.error('Error attaching authentication headers:', e);
  }
  
  return headers;
};

export const api = {
  get: async (path: string) => {
    const headers = await getHeaders();
    const res = await fetch(`${getBackendUrl()}${path}`, {
      method: 'GET',
      headers: {
        ...headers,
        'Accept': 'application/json',
      },
    });
    
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Network request failed' }));
      throw new Error(err.detail || 'An unexpected error occurred.');
    }
    return res.json();
  },
  
  post: async (path: string, body: any, isJson = true) => {
    const headers = await getHeaders();
    const fetchHeaders: Record<string, string> = {
      ...headers,
    };
    
    if (isJson) {
      fetchHeaders['Content-Type'] = 'application/json';
    }
    
    const res = await fetch(`${getBackendUrl()}${path}`, {
      method: 'POST',
      headers: fetchHeaders,
      body: isJson ? JSON.stringify(body) : body,
    });
    
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Request submission failed' }));
      throw new Error(err.detail || 'An unexpected error occurred.');
    }
    return res.json();
  },

  delete: async (path: string) => {
    const headers = await getHeaders();
    const res = await fetch(`${getBackendUrl()}${path}`, {
      method: 'DELETE',
      headers: {
        ...headers,
        'Accept': 'application/json',
      },
    });
    
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Request deletion failed' }));
      throw new Error(err.detail || 'An unexpected error occurred.');
    }
    return res.json();
  },
};

