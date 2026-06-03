import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY || '';

// Detect if we should use mock auth for testing when keys are missing
export const isMockAuth = !supabaseUrl || !supabaseAnonKey;

// Real client or mock client implementation
export const supabase = !isMockAuth
  ? createClient(supabaseUrl, supabaseAnonKey)
  : {
      auth: {
        getSession: async () => {
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
          // Trigger first callback invocation with current session
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
