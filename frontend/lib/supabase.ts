import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY || '';

// Detect if we are on localhost
const isLocalhost = typeof window !== 'undefined' && 
  (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');

// Only use mock auth on localhost development environments when keys are missing
export const isMockAuth = (!supabaseUrl || !supabaseAnonKey) && isLocalhost;

// Real client or mock/error client implementation
export const supabase = (!isMockAuth && supabaseUrl && supabaseAnonKey)
  ? createClient(supabaseUrl, supabaseAnonKey)
  : {
      auth: {
        getSession: async () => {
          // If we are not on localhost and keys are missing, return a configuration error
          if (!isLocalhost && (!supabaseUrl || !supabaseAnonKey)) {
            return {
              data: { session: null },
              error: { message: "Supabase environment variables are missing. Please configure NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY in your Vercel settings." } as any
            };
          }
          if (typeof window !== 'undefined') {
            const mockUser = localStorage.getItem('claimsure_mock_user');
            if (mockUser) {
              const userObj = JSON.parse(mockUser);
              return {
                data: {
                  session: {
                    user: userObj,
                    access_token: 'mock-developer-jwt-token'
                  }
                },
                error: null
              };
            }
          }
          return { data: { session: null }, error: null };
        },
        onAuthStateChange: (callback: any) => {
          if (!isLocalhost && (!supabaseUrl || !supabaseAnonKey)) {
            callback('SIGNED_OUT', null);
            return {
              data: {
                subscription: {
                  unsubscribe: () => {}
                }
              }
            };
          }
          if (typeof window !== 'undefined') {
            const mockUser = localStorage.getItem('claimsure_mock_user');
            if (mockUser) {
              const userObj = JSON.parse(mockUser);
              callback('SIGNED_IN', { user: userObj, access_token: 'mock-developer-jwt-token' });
            } else {
              callback('SIGNED_OUT', null);
            }
          }
          return {
            data: {
              subscription: {
                unsubscribe: () => {}
              }
            }
          };
        },
        signUp: async ({ email, password }: any) => {
          if (!isLocalhost && (!supabaseUrl || !supabaseAnonKey)) {
            return {
              data: { user: null, session: null },
              error: { message: "Supabase environment variables are missing. Please configure NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY in your Vercel settings." } as any
            };
          }
          const user = { 
            id: 'mock-supabase-user-uuid', 
            email, 
            user_metadata: {} 
          };
          if (typeof window !== 'undefined') {
            localStorage.setItem('claimsure_mock_user', JSON.stringify(user));
          }
          return {
            data: {
              user,
              session: { user, access_token: 'mock-developer-jwt-token' }
            },
            error: null
          };
        },
        signInWithPassword: async ({ email, password }: any) => {
          if (!isLocalhost && (!supabaseUrl || !supabaseAnonKey)) {
            return {
              data: { user: null, session: null },
              error: { message: "Supabase environment variables are missing. Please configure NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY in your Vercel settings." } as any
            };
          }
          const user = { 
            id: 'mock-supabase-user-uuid', 
            email, 
            user_metadata: {} 
          };
          if (typeof window !== 'undefined') {
            localStorage.setItem('claimsure_mock_user', JSON.stringify(user));
          }
          return {
            data: {
              user,
              session: { user, access_token: 'mock-developer-jwt-token' }
            },
            error: null
          };
        },
        signOut: async () => {
          if (typeof window !== 'undefined') {
            localStorage.removeItem('claimsure_mock_user');
          }
          return { error: null };
        }
      }
    } as any;
