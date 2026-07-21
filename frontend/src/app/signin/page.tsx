'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Cookies from 'js-cookie';
import { api } from '@/lib/api';
import { Sun, Moon, Quote, CheckCircle, ShieldAlert } from 'lucide-react';
import NyayaLogo from '@/components/NyayaLogo';

export default function SignInPage() {
  const router = useRouter();
  const [tab, setTab] = useState<'signin' | 'signup'>('signin');
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  
  // Form fields
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  
  // UI states
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    // Resolve theme on load
    const isDark = document.documentElement.classList.contains('dark');
    setTheme(isDark ? 'dark' : 'light');
  }, []);

  const toggleTheme = () => {
    const nextTheme = theme === 'light' ? 'dark' : 'light';
    if (nextTheme === 'dark') {
      document.documentElement.classList.add('dark');
      localStorage.setItem('nyaya-theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('nyaya-theme', 'light');
    }
    setTheme(nextTheme);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setSuccessMsg(null);
    setLoading(true);

    if (!email || !password) {
      setErrorMsg('Please fill in all fields.');
      setLoading(false);
      return;
    }

    try {
      if (tab === 'signup') {
        // Registration Flow
        await api.post('/api/v1/auth/signup', {
          username: email,
          password: password,
        });

        setSuccessMsg('Account created successfully! Please sign in with your credentials.');
        setTab('signin');
        setPassword('');
        setFullName('');
        return;
      }

      // Login Flow
      const response = await api.post('/api/v1/auth/signin', {
        username: email,
        password: password,
      });

      const { access_token, username, user_id } = response.data;

      // Save token in cookie with Max-Age 2 days (7 days safety)
      Cookies.set('nyaya_token', access_token, { expires: 7, path: '/' });
      
      // Save user profile details locally
      localStorage.setItem('nyaya_username', username);
      localStorage.setItem('nyaya_user_id', user_id);

      // Route to dashboard
      router.push('/dashboard');
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setErrorMsg(typeof detail === 'string' ? detail : 'Authentication failed. Please verify your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col lg:flex-row min-h-screen">
      {/* ==================== LEFT PANEL (Visual/Marketing) ==================== */}
      <div className="hidden lg:flex w-1/2 bg-amazon-mist flex-col justify-between p-12 relative overflow-hidden">
        {/* Background Pattern */}
        <div className="absolute inset-0 dot-pattern pointer-events-none"></div>

        {/* Logo */}
        <div 
          onClick={() => router.push('/')}
          className="relative z-10 flex items-center gap-3 cursor-pointer hover:opacity-80 transition-opacity"
        >
          <NyayaLogo height={32} />
          <div>
            <div className="font-display font-semibold text-[15px] tracking-tight leading-none text-primary">
              Nyaya AI
            </div>
            <div className="text-[9px] uppercase tracking-[0.18em] text-muted mt-1 font-mono">
              Legal Intelligence Platform
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="relative z-10">
          <h1 className="font-display font-bold text-primary tracking-tight mb-8 leading-[1.05] text-[48px]">
            Indian Legal
            <br />
            Intelligence Platform
          </h1>

          {/* Statutory Intelligence Capabilities Card */}
          <div className="bg-surface border-kite p-6 rounded-lg max-w-md shadow-sm">
            <div className="flex items-center gap-1.5 mb-4">
              <ShieldAlert className="w-4 h-4 text-rose-gold" />
              <span className="text-xs font-mono text-muted uppercase tracking-wider">
                Statutory Compliance Audit
              </span>
            </div>
            <p className="text-[14px] mb-4 text-primary leading-relaxed">
              Audits contracts in seconds for void post-employment restraints under <strong>ICA §27</strong> and payment timeline violations under <strong>MSMED Act §15</strong>.
            </p>
            <div className="flex flex-wrap gap-2 pt-4 border-kite-t">
              <span className="px-2 py-1.5 rounded text-[10px] font-mono bg-amazon-mist text-secondary font-medium">
                100+ Landmark Precedents
              </span>
              <span className="px-2 py-1.5 rounded text-[10px] font-mono bg-amazon-mist text-secondary font-medium">
                33K+ Statutory Sections
              </span>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="relative z-10 text-xs text-muted">
          © 2026 Nyaya AI · Built by Mehtab Singh
        </div>
      </div>

      {/* ==================== RIGHT PANEL (Form) ==================== */}
      <div className="flex-1 flex flex-col items-center justify-center p-6 bg-page relative">
        {/* Theme Toggle (Top Right) */}
        <div className="absolute top-6 right-6">
          <button
            className="theme-toggle"
            onClick={toggleTheme}
            aria-label="Toggle theme"
          >
            <div className="theme-toggle-thumb">
              {theme === 'light' ? (
                <Sun className="w-3 h-3 text-[#1A0A05]" />
              ) : (
                <Moon className="w-3 h-3 text-[#1A0A05]" />
              )}
            </div>
          </button>
        </div>

        {/* Form Card */}
        <div className="w-full max-w-md bg-surface border-kite rounded-xl p-8 lg:p-10 shadow-sm">
          {/* Logo Header */}
          <div className="flex flex-col items-center mb-8">
            <NyayaLogo 
              height={44} 
              className="mb-4 cursor-pointer hover:opacity-80 transition-opacity" 
              onClick={() => router.push('/')}
            />
            <h2 className="font-display text-2xl font-bold text-primary">
              {tab === 'signin' ? 'Welcome to Nyaya' : 'Start your free trial'}
            </h2>
            <p className="text-sm text-secondary mt-1 text-center">
              {tab === 'signin'
                ? 'Sign in to your legal intelligence dashboard'
                : '14-day access to all statutory intelligence features'}
            </p>
          </div>

           {/* Tab Toggle */}
          <div className="flex p-1 bg-amazon-mist rounded-md border border-[var(--black-kite-15)] mb-6">
            <button
              onClick={() => {
                setTab('signin');
                setErrorMsg(null);
                setSuccessMsg(null);
              }}
              className={`flex-1 py-2 text-sm font-medium rounded transition-all ${
                tab === 'signin' ? 'bg-surface text-primary shadow-sm' : 'text-secondary hover:text-primary'
              }`}
            >
              Sign In
            </button>
            <button
              onClick={() => {
                setTab('signup');
                setErrorMsg(null);
                setSuccessMsg(null);
              }}
              className={`flex-1 py-2 text-sm font-medium rounded transition-all ${
                tab === 'signup' ? 'bg-surface text-primary shadow-sm' : 'text-secondary hover:text-primary'
              }`}
            >
              Create Account
            </button>
          </div>

          {/* Success Message banner */}
          {successMsg && (
            <div className="mb-4 p-3 bg-green-100 dark:bg-green-950/40 border border-green-200 dark:border-green-900 rounded-md flex items-start gap-2.5">
              <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400 mt-0.5 flex-shrink-0" />
              <p className="text-xs text-green-700 dark:text-green-300 leading-normal">{successMsg}</p>
            </div>
          )}

          {/* Error Message banner */}
          {errorMsg && (
            <div className="mb-4 p-3 bg-red-100 dark:bg-red-950/40 border border-red-200 dark:border-red-900 rounded-md flex items-start gap-2.5">
              <ShieldAlert className="w-4 h-4 text-red-600 dark:text-red-400 mt-0.5 flex-shrink-0" />
              <p className="text-xs text-red-700 dark:text-red-300 leading-normal">{errorMsg}</p>
            </div>
          )}

          {/* Form */}
          <form className="space-y-4" onSubmit={handleSubmit}>
            {/* Name Field (Visible during signup) */}
            {tab === 'signup' && (
              <div>
                <label className="block text-xs font-medium text-secondary mb-1.5">
                  Full Name
                </label>
                <input
                  type="text"
                  placeholder="Ananya Krishnan"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="input-field"
                />
              </div>
            )}

            {/* Email Field */}
            <div>
              <label className="block text-xs font-medium text-secondary mb-1.5">
                Email Address
              </label>
              <input
                type="email"
                placeholder="advocate@nyaya.ai"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="input-field"
              />
            </div>

            {/* Password Field */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-xs font-medium text-secondary">Password</label>
                {tab === 'signin' && (
                  <a
                    href="#"
                    onClick={(e) => {
                      e.preventDefault();
                      alert('Forgot password is coming soon. Please contact administrator.');
                    }}
                    className="text-xs text-[var(--toxic-orange)] hover:underline font-medium"
                  >
                    Forgot?
                  </a>
                )}
              </div>
              <input
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="input-field"
              />
            </div>

            {/* CTA Button */}
            <button
              type="submit"
              disabled={loading}
              className="btn-primary mt-2 flex items-center justify-center gap-2"
            >
              {loading ? (
                <div className="w-4 h-4 border-2 border-t-transparent border-[#1A0A05] rounded-full animate-spin"></div>
              ) : tab === 'signin' ? (
                'Sign In'
              ) : (
                'Create Account'
              )}
            </button>
          </form>

          {/* Divider */}
          <div className="flex items-center my-6">
            <div className="flex-1 h-px bg-[var(--black-kite-15)]"></div>
            <span className="px-3 text-xs text-muted uppercase tracking-wider font-medium">
              Or continue with
            </span>
            <div className="flex-1 h-px bg-[var(--black-kite-15)]"></div>
          </div>

          {/* Third-Party Auth */}
          <div className="flex flex-col gap-3">
            <button
              onClick={() => alert('Google authentication is coming soon!')}
              className="btn-outline w-full"
            >
              <svg width="16" height="16" viewBox="0 0 24 24">
                <path
                  fill="#4285F4"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="#34A853"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="#FBBC05"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                />
                <path
                  fill="#EA4335"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                />
              </svg>
              Continue with Google
            </button>
          </div>

          {/* Legal Note */}
          <p className="text-center text-xs text-muted mt-8 leading-relaxed">
            By continuing, you agree to our{' '}
            <a href="#" className="underline hover:text-primary">
              Terms
            </a>{' '}
            and{' '}
            <a href="#" className="underline hover:text-primary">
              Privacy Policy
            </a>
            .
          </p>
        </div>
      </div>
    </div>
  );
}
