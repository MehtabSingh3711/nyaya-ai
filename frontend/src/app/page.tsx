'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Cookies from 'js-cookie';
import {
  Sun,
  Moon,
  ArrowRight,
  ShieldAlert,
  Clock,
  Sparkles,
  TrendingUp,
  FileText,
  Lock,
  Globe,
  Database,
  ArrowUpRight,
  AlertTriangle,
  Scale,
  BrainCircuit,
  MessageSquare,
  CheckCircle,
  HelpCircle
} from 'lucide-react';
import NyayaLogo from '@/components/NyayaLogo';

export default function LandingPage() {
  const router = useRouter();
  const [theme, setTheme] = useState<'light' | 'dark'>('light');

  useEffect(() => {
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

  const handleEnterDashboard = (e: React.MouseEvent) => {
    e.preventDefault();
    const token = Cookies.get('nyaya_token');
    if (token) {
      router.push('/dashboard');
    } else {
      router.push('/signin');
    }
  };

  return (
    <div className="min-h-screen bg-page text-primary transition-all duration-300">
      {/* ==================== NAVBAR ==================== */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-surface/80 backdrop-blur-md border-b border-[var(--black-kite-15)]">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => router.push('/')}>
            <NyayaLogo height={28} />
            <div>
              <div className="font-display font-semibold text-[15px] tracking-tight leading-none text-primary">
                Nyaya AI
              </div>
              <div className="text-[9px] uppercase tracking-[0.18em] text-muted mt-1 font-mono">
                Legal Intelligence Platform
              </div>
            </div>
          </div>

          {/* Center Links */}
          <div className="hidden md:flex items-center gap-6">
            <a href="#features" className="text-[13px] font-medium text-secondary hover:text-primary transition-colors">
              Features
            </a>
            <a href="#precedents" className="text-[13px] font-medium text-secondary hover:text-primary transition-colors">
              Precedents
            </a>
            <a href="#security" className="text-[13px] font-medium text-secondary hover:text-primary transition-colors">
              Security
            </a>
            <a href="#faq" className="text-[13px] font-medium text-secondary hover:text-primary transition-colors">
              FAQ
            </a>
          </div>

          {/* Right Actions */}
          <div className="flex items-center gap-3">
            {/* Theme toggle */}
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

            <button
              onClick={() => router.push('/signin')}
              className="hidden sm:flex btn-outline px-4 py-2 rounded-md text-[13px] flex items-center gap-1.5 whitespace-nowrap"
            >
              Sign In
            </button>

            <button
              onClick={handleEnterDashboard}
              className="btn-primary px-4 py-2 rounded-md text-[13px] flex items-center gap-1.5 whitespace-nowrap"
            >
              Enter Dashboard
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </nav>

      {/* ==================== HERO ==================== */}
      <section className="relative pt-32 pb-20 lg:pt-40 lg:pb-28 overflow-hidden">
        <div className="absolute inset-0 dot-pattern pointer-events-none"></div>
        <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-b from-transparent to-[var(--morning-snow)] pointer-events-none"></div>

        <div className="relative max-w-5xl mx-auto px-6 text-center">
          {/* Floating tags */}
          <div className="hidden lg:block">
            <div className="float-tag absolute -left-4 top-8" style={{ transform: 'rotate(-4deg)' }}>
              <div className="bg-red-100 dark:bg-red-950/40 text-red-700 dark:text-red-300 border border-red-300 dark:border-red-900 px-3 py-1.5 rounded-md text-[10px] font-bold uppercase tracking-wider flex items-center gap-1.5 shadow-lg">
                <AlertTriangle className="w-3 h-3" />
                § 2.3 VOID · ICA §27
              </div>
            </div>
            <div className="float-tag absolute right-0 top-16" style={{ transform: 'rotate(3deg)' }}>
              <div className="bg-yellow-100 dark:bg-yellow-950/40 text-yellow-700 dark:text-yellow-300 border border-yellow-300 dark:border-yellow-900 px-3 py-1.5 rounded-md text-[10px] font-bold uppercase tracking-wider flex items-center gap-1.5 shadow-lg">
                <Clock className="w-3 h-3" />
                § 4.1 REVIEW · MSME §15
              </div>
            </div>
            <div className="float-tag absolute -left-8 bottom-32" style={{ transform: 'rotate(2deg)' }}>
              <div className="risk-safe px-3 py-1.5 rounded-md text-[10px] font-bold uppercase tracking-wider flex items-center gap-1.5 shadow-lg">
                <CheckCircle className="w-3 h-3" />
                § 1.0 COMPLIANT
              </div>
            </div>
            <div className="float-tag absolute right-4 bottom-20" style={{ transform: 'rotate(-2deg)' }}>
              <div className="bg-surface border-kite px-3 py-1.5 rounded-md text-[10px] font-mono font-semibold text-primary flex items-center gap-1.5 shadow-lg">
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--toxic-orange)] animate-pulse"></span>
                95% confidence
              </div>
            </div>
          </div>

          {/* Eyebrow */}
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-[var(--black-kite-15)] bg-surface mb-8">
            <span className="w-1.5 h-1.5 rounded-full bg-safe-text"></span>
            <span className="text-[11px] font-medium text-secondary uppercase tracking-[0.15em]">
              Indian Legal Contract Intelligence
            </span>
          </div>

          {/* Title */}
          <h1
            className="font-display font-bold text-primary leading-[0.95] tracking-tighter mb-8"
            style={{ fontSize: 'clamp(48px, 9vw, 92px)' }}
          >
            Know what
            <br />
            you <span className="text-[var(--toxic-orange)]">sign</span>
            <span className="text-[var(--toxic-orange)]">.</span>
          </h1>

          {/* Description */}
          <p className="mt-8 text-[17px] sm:text-[19px] text-secondary leading-relaxed max-w-2xl mx-auto">
            Nyaya AI analyzes Indian legal contracts in seconds — detecting void clauses, statutory
            violations under{' '}
            <span className="font-mono text-primary font-medium">ICA §27</span>,{' '}
            <span className="font-mono text-primary font-medium">MSME Act §15</span>, and compliance
            risks before you sign.
          </p>

          {/* CTAs */}
          <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-3">
            <button
              onClick={handleEnterDashboard}
              className="btn-primary px-7 py-3.5 rounded-md text-[14px] flex items-center gap-2 w-full sm:w-auto justify-center"
            >
              <Scale className="w-4 h-4" />
              Scan a Contract
            </button>
            <button
              onClick={handleEnterDashboard}
              className="btn-outline px-7 py-3.5 rounded-md text-[14px] flex items-center gap-2 w-full sm:w-auto justify-center"
            >
              <Sparkles className="w-4 h-4 text-rose-gold" />
              Ask Legal AI
            </button>
          </div>

          {/* Stats Row */}
          <div className="mt-16 flex items-center justify-center gap-6 sm:gap-12">
            <div className="text-center">
              <div className="font-display font-bold text-[28px] sm:text-[32px] text-primary leading-none">
                100<span className="text-[var(--toxic-orange)]">+</span>
              </div>
              <div className="text-[10px] uppercase tracking-wider text-muted mt-2 font-medium">
                Landmark Precedents
              </div>
            </div>
            <div className="w-px h-10 bg-[var(--black-kite-15)]"></div>
            <div className="text-center">
              <div className="font-display font-bold text-[28px] sm:text-[32px] text-primary leading-none">
                33K<span className="text-[var(--toxic-orange)]">+</span>
              </div>
              <div className="text-[10px] uppercase tracking-wider text-muted mt-2 font-medium">
                Statutory Sections
              </div>
            </div>
            <div className="w-px h-10 bg-[var(--black-kite-15)]"></div>
            <div className="text-center">
              <div className="font-display font-bold text-[28px] sm:text-[32px] text-primary leading-none">
                90<span className="text-[var(--toxic-orange)]">%</span>
              </div>
              <div className="text-[10px] uppercase tracking-wider text-muted mt-2 font-medium">
                Citation Precision
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ==================== FEATURES ==================== */}
      <section id="features" className="relative py-20 lg:py-28 border-t border-[var(--black-kite-15)]">
        <div className="max-w-7xl mx-auto px-6">
          <div className="max-w-2xl mb-14">
            <div className="flex items-center gap-2 mb-4">
              <div className="h-px w-8 bg-[var(--toxic-orange)]"></div>
              <span className="text-[11px] font-mono font-semibold uppercase tracking-[0.2em] text-[var(--toxic-orange)]">
                01 — Capabilities
              </span>
            </div>
            <h2 className="font-display font-bold text-primary tracking-tight text-3xl md:text-5xl">
              Statutory intelligence
              <br />
              built for Indian law.
            </h2>
            <p className="mt-5 text-[16px] text-secondary leading-relaxed">
              Not a generic LLM wrapper. Nyaya AI is trained on Indian statutes, landmark court precedents,
              and regulatory frameworks — purpose-built for the contracts you actually sign.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Feature 1 */}
            <div className="bg-surface border-kite rounded-lg p-7">
              <div className="flex items-start justify-between mb-6">
                <div
                  className="w-11 h-11 rounded-md flex items-center justify-center border"
                  style={{
                    background: 'rgba(115, 54, 53, 0.08)',
                    borderColor: 'rgba(115, 54, 53, 0.2)',
                    color: 'var(--garnet)'
                  }}
                >
                  <ShieldAlert className="w-5 h-5" />
                </div>
                <span className="text-[10px] font-mono text-muted">F1</span>
              </div>
              <div className="text-[10px] font-mono font-semibold uppercase tracking-wider mb-2 text-rose-gold">
                § 27 · Indian Contract Act, 1872
              </div>
              <h3 className="font-display font-semibold text-[20px] text-primary leading-tight mb-3">
                Restraint of Trade Detection
              </h3>
              <p className="text-[13.5px] text-secondary leading-relaxed mb-6">
                Automatically flags non-compete and restraint-of-trade clauses that are void under
                Section 27. Cross-references landmark precedents to evaluate enforceability.
              </p>
              <div className="pt-5 border-kite-t flex items-center justify-between">
                <span className="bg-red-100 dark:bg-red-950/40 text-red-700 dark:text-red-300 border border-red-300 dark:border-red-900 px-2.5 py-1 rounded text-[9px] font-bold uppercase tracking-wider flex items-center gap-1">
                  <AlertTriangle className="w-2.5 h-2.5" /> Void · ICA §27
                </span>
              </div>
            </div>

            {/* Feature 2 */}
            <div className="bg-surface border-kite rounded-lg p-7">
              <div className="flex items-start justify-between mb-6">
                <div
                  className="w-11 h-11 rounded-md flex items-center justify-center border"
                  style={{
                    background: 'rgba(53, 30, 28, 0.06)',
                    borderColor: 'var(--black-kite-15)',
                    color: 'var(--black-kite)'
                  }}
                >
                  <Clock className="w-5 h-5" />
                </div>
                <span className="text-[10px] font-mono text-muted">F2</span>
              </div>
              <div className="text-[10px] font-mono font-semibold uppercase tracking-wider mb-2 text-[var(--rose-gold)]">
                § 15 · MSMED Act, 2006
              </div>
              <h3 className="font-display font-semibold text-[20px] text-primary leading-tight mb-3">
                MSME Payment Violations
              </h3>
              <p className="text-[13.5px] text-secondary leading-relaxed mb-6">
                Identifies payment terms exceeding the statutory 45-day MSME threshold. Provides legal
                remedies and interest computations under Section 16 directly on the dashboard findings.
              </p>
              <div className="pt-5 border-kite-t flex items-center justify-between">
                <span className="bg-yellow-100 dark:bg-yellow-950/40 text-yellow-700 dark:text-yellow-300 border border-yellow-300 dark:border-yellow-900 px-2.5 py-1 rounded text-[9px] font-bold uppercase tracking-wider flex items-center gap-1">
                  <Clock className="w-2.5 h-2.5" /> Overdue · MSMED §15
                </span>
              </div>
            </div>

            {/* Feature 3 */}
            <div className="bg-surface border-kite rounded-lg p-7">
              <div className="flex items-start justify-between mb-6">
                <div
                  className="w-11 h-11 rounded-md flex items-center justify-center border"
                  style={{
                    background: 'rgba(160, 201, 203, 0.15)',
                    borderColor: 'var(--aqua-mist)',
                    color: 'var(--muted-copper)'
                  }}
                >
                  <Sparkles className="w-5 h-5" />
                </div>
                <span className="text-[10px] font-mono text-muted">F3</span>
              </div>
              <div className="text-[10px] font-mono font-semibold uppercase tracking-wider mb-2 text-rose-gold">
                Next-Gen RAG Architecture
              </div>
              <h3 className="font-display font-semibold text-[20px] text-primary leading-tight mb-3">
                Cloud LLM Cascade
              </h3>
              <p className="text-[13.5px] text-secondary leading-relaxed mb-6">
                Escalates verification from Groq (Llama 3.1) to Gemini and OpenRouter. Leverages dense
                BGE-M3 representations and Jina rerankers for a ₹0.00-cost system with sub-3s response.
              </p>
              <div className="pt-5 border-kite-t flex items-center justify-between">
                <span className="risk-safe px-2.5 py-1 rounded text-[9px] font-bold uppercase tracking-wider flex items-center gap-1">
                  <CheckCircle className="w-2.5 h-2.5" /> Grounded · Cite-or-Refuse
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ==================== PRECEDENTS ==================== */}
      <section id="precedents" className="relative py-20 lg:py-28 border-t border-[var(--black-kite-15)]">
        <div className="max-w-7xl mx-auto px-6">
          <div className="max-w-2xl mb-14">
            <div className="flex items-center gap-2 mb-4">
              <div className="h-px w-8 bg-[var(--toxic-orange)]"></div>
              <span className="text-[11px] font-mono font-semibold uppercase tracking-[0.2em] text-[var(--toxic-orange)]">
                02 — Case Law
              </span>
            </div>
            <h2 className="font-display font-bold text-primary tracking-tight text-3xl md:text-5xl">
              100 Landmark Precedents.
            </h2>
            <p className="mt-5 text-[16px] text-secondary leading-relaxed">
              We ingested and indexed 100 curated judicial precedents from the Supreme Court and High Courts. 
              The Contract Scanner cross-references these case rulings to verify the legal enforceability of clauses.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-surface border-kite rounded-lg p-6">
              <h4 className="font-display font-semibold text-lg text-primary mb-2">
                Niranjan Shankar Golikari v. Century Spinning & Mfg. Co.
              </h4>
              <span className="text-xs font-mono text-[var(--rose-gold)] block mb-4">1967 SCR (2) 378</span>
              <p className="text-xs text-secondary leading-relaxed">
                Holds that negative covenants operative during the period of employment when the employee 
                is bound to serve his employer exclusively are generally not regarded as restraint of trade under Section 27.
              </p>
            </div>
            <div className="bg-surface border-kite rounded-lg p-6">
              <h4 className="font-display font-semibold text-lg text-primary mb-2">
                Superintendence Company of India v. Krishan Murgai
              </h4>
              <span className="text-xs font-mono text-[var(--rose-gold)] block mb-4">1980 SCR (3) 1278</span>
              <p className="text-xs text-secondary leading-relaxed">
                Confirms that post-service restrictive covenants (non-competes extending past termination) 
                are entirely void and unenforceable under Section 27 of the Indian Contract Act, without exception.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ==================== SECURITY ==================== */}
      <section id="security" className="relative py-20 lg:py-28 border-t border-[var(--black-kite-15)]">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <div className="h-px w-8 bg-[var(--toxic-orange)]"></div>
                <span className="text-[11px] font-mono font-semibold uppercase tracking-[0.2em] text-[var(--toxic-orange)]">
                  03 — Enterprise Safety
                </span>
              </div>
              <h2 className="font-display font-bold text-primary tracking-tight text-3xl md:text-5xl mb-6">
                Privacy-first legal analysis
              </h2>
              <p className="text-[15.5px] text-secondary leading-relaxed mb-6">
                We know legal documents are highly confidential. Nyaya AI secures your data at every layer
                using advanced security architectures:
              </p>
              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <div className="w-5 h-5 rounded-full bg-safe-bg text-safe-text flex items-center justify-center flex-shrink-0 mt-0.5">
                    <CheckCircle className="w-3.5 h-3.5" />
                  </div>
                  <div>
                    <span className="text-sm font-semibold text-primary block">Data Isolation</span>
                    <span className="text-xs text-secondary">
                      Multi-tenant data tagging isolates and restricts contract clauses by user ID.
                    </span>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-5 h-5 rounded-full bg-safe-bg text-safe-text flex items-center justify-center flex-shrink-0 mt-0.5">
                    <CheckCircle className="w-3.5 h-3.5" />
                  </div>
                  <div>
                    <span className="text-sm font-semibold text-primary block">Secure Session Cookies</span>
                    <span className="text-xs text-secondary">
                      Stateless session JWTs are processed server-side, preventing client-side data leaks.
                    </span>
                  </div>
                </div>
              </div>
            </div>
            <div className="bg-amazon-mist border border-[var(--black-kite-15)] rounded-xl p-8 flex flex-col justify-center">
              <Lock className="w-12 h-12 text-rose-gold mb-6" />
              <h3 className="font-display font-bold text-2xl text-primary mb-3">Enterprise Grade Guards</h3>
              <p className="text-sm text-secondary leading-relaxed mb-6">
                Your data is never utilized for LLM model training. All documents reside strictly in secure, 
                isolated memory buckets during scanning and are deleted immediately upon completion.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ==================== FAQ ==================== */}
      <section id="faq" className="relative py-20 lg:py-28 border-t border-[var(--black-kite-15)] bg-surface">
        <div className="max-w-4xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="font-display font-bold text-primary text-3xl md:text-5xl">
              Frequently Asked Questions
            </h2>
            <p className="text-secondary mt-4">Everything you need to know about Nyaya AI</p>
          </div>

          <div className="space-y-6">
            <div className="border-b border-[var(--black-kite-15)] pb-6">
              <h4 className="font-semibold text-primary text-[15px] mb-2">How accurate is the compliance scanner?</h4>
              <p className="text-xs text-secondary leading-relaxed">
                Nyaya AI uses a strict <strong>Cite-or-Refuse</strong> mechanism. We achieve &gt;90% citation precision. 
                If the model does not have sufficient context from official Indian central acts or court rulings, it refuses to assess rather than generating legal hallucinations.
              </p>
            </div>
            <div className="border-b border-[var(--black-kite-15)] pb-6">
              <h4 className="font-semibold text-primary text-[15px] mb-2">Is my upload contract stored permanently?</h4>
              <p className="text-xs text-secondary leading-relaxed">
                The text is chunked and temporarily processed. The clauses are saved locally under your user ID to allow 
                dashboard auditing and PDF export, but are protected with strict tenant filters and can be deleted at any time.
              </p>
            </div>
            <div className="pb-6">
              <h4 className="font-semibold text-primary text-[15px] mb-2">Why is it free?</h4>
              <p className="text-xs text-secondary leading-relaxed">
                We designed a specialized cloud cascade architecture (Groq Llama 3.1 &gt; Gemini &gt; OpenRouter) 
                utilizing free-tier cloud endpoints to run the platform at exactly ₹0.00 infrastructure cost.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ==================== FOOTER ==================== */}
      <footer className="bg-surface border-t border-[var(--black-kite-15)] py-12">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="text-xs text-muted">
            © 2026 Nyaya AI · Built by Mehtab Singh
          </div>
          <div className="flex gap-4 text-xs text-muted">
            <a href="#" className="hover:text-primary">Terms of Service</a>
            <span>·</span>
            <a href="#" className="hover:text-primary">Privacy Policy</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
