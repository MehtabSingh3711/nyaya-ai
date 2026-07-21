'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Cookies from 'js-cookie';
import { LogOut, Sun, Moon, Bell } from 'lucide-react';
import NyayaLogo from './NyayaLogo';

interface HeaderProps {
  workspaceLabel?: string;
  showSearch?: boolean;
  onSearchChange?: (val: string) => void;
  searchValue?: string;
}

export default function Header({
  workspaceLabel = 'Workspace',
  showSearch = false,
  onSearchChange,
  searchValue = '',
}: HeaderProps) {
  const router = useRouter();
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const [username, setUsername] = useState<string>('User');

  useEffect(() => {
    // Resolve theme on client mount
    const isDark = document.documentElement.classList.contains('dark');
    setTheme(isDark ? 'dark' : 'light');

    // Retrieve username from localStorage
    const savedUsername = localStorage.getItem('nyaya_username');
    if (savedUsername) {
      setUsername(savedUsername);
    }
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

  const handleLogout = () => {
    Cookies.remove('nyaya_token', { path: '/' });
    localStorage.removeItem('nyaya_username');
    localStorage.removeItem('nyaya_user_id');
    router.push('/signin');
  };

  const getInitials = (name: string) => {
    if (!name) return 'U';
    const clean = name.replace(/[^a-zA-Z0-9 ]/g, '').trim();
    if (!clean) return 'U';
    const parts = clean.split(/\s+/);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return clean.substring(0, 2).toUpperCase();
  };

  return (
    <header className="bg-surface border-kite-b z-30 flex-shrink-0">
      <div className="px-6 py-3 flex items-center justify-between gap-6">
        {/* Logo and Workspace detail */}
        <div className="flex items-center gap-3 cursor-pointer" onClick={() => router.push('/dashboard')}>
          <NyayaLogo height={28} />
          <div>
            <div className="font-display font-semibold text-[15px] tracking-tight leading-none text-primary">
              Nyaya AI
            </div>
            <div className="text-[9px] uppercase tracking-[0.18em] text-muted mt-1 font-mono">
              Legal Intelligence Platform
            </div>
          </div>
          {workspaceLabel && (
            <div className="h-5 w-px bg-[var(--black-kite-15)] hidden sm:block"></div>
          )}
          {workspaceLabel && (
            <span className="text-[10px] text-muted font-mono uppercase tracking-wider hidden sm:inline-block">
              {workspaceLabel}
            </span>
          )}
        </div>

        {/* Global Search (optional) */}
        {showSearch && (
          <div className="flex-1 max-w-md hidden md:block relative">
            <svg
              className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
            <input
              type="text"
              placeholder="Search contracts, clauses, statutes..."
              value={searchValue}
              onChange={(e) => onSearchChange && onSearchChange(e.target.value)}
              className="w-full bg-page border-kite rounded-md pl-10 pr-4 py-2 text-sm text-primary placeholder:text-muted outline-none focus:border-aqua-mist focus:ring-4 focus:ring-aqua-mist-soft transition-all"
            />
          </div>
        )}

        {/* Right side settings, toggles, profile */}
        <div className="flex items-center gap-4">
          <button className="relative text-secondary hover:text-primary p-1 rounded-full hover:bg-page transition-colors">
            <Bell className="w-5 h-5" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-[var(--toxic-orange)] rounded-full"></span>
          </button>

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

          <div className="flex items-center gap-2">
            <div
              className="w-9 h-9 rounded-full bg-gradient-to-br from-[var(--rose-gold)] to-[var(--muted-copper)] flex items-center justify-center text-white text-xs font-semibold border border-[var(--black-kite-15)] select-none"
              title={username}
            >
              {getInitials(username)}
            </div>

            <button
              onClick={handleLogout}
              className="p-2 text-secondary hover:text-[var(--garnet)] hover:bg-page rounded-full transition-all"
              title="Sign Out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
