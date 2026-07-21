'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Header from '@/components/Header';
import { api } from '@/lib/api';
import {
  FileText,
  AlertTriangle,
  MessageSquare,
  IndianRupee,
  Plus,
  Play,
  Trash2,
  AlertCircle,
  CheckCircle,
  ExternalLink,
  Loader2,
  TrendingUp
} from 'lucide-react';

interface ScanRecord {
  scan_id: string;
  contract_name: string;
  clause_count: number;
  status: string;
  risk_level: 'high' | 'medium' | 'low' | null;
  scan_date: string;
}

interface ChatSession {
  session_id: string;
  title: string;
  created_at: string;
}

interface DashboardStats {
  total_contracts_scanned: number;
  total_risks_identified: number;
  total_api_cost: string;
}

export default function DashboardPage() {
  const router = useRouter();
  const [stats, setStats] = useState<DashboardStats>({
    total_contracts_scanned: 0,
    total_risks_identified: 0,
    total_api_cost: '₹0.00'
  });
  const [scans, setScans] = useState<ScanRecord[]>([]);
  const [chats, setChats] = useState<ChatSession[]>([]);
  const [username, setUsername] = useState('User');
  const [loading, setLoading] = useState(true);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  useEffect(() => {
    // Read local storage info
    const saved = localStorage.getItem('nyaya_username');
    if (saved) {
      setUsername(saved);
    }
    
    // Fetch live dashboard metrics
    const fetchDashboardData = async () => {
      try {
        const [statsRes, scansRes, chatsRes] = await Promise.all([
          api.get('/api/v1/dashboard/stats'),
          api.get('/api/v1/contracts/scans'),
          api.get('/api/v1/chat/sessions'),
        ]);

        setStats(statsRes.data);
        setScans(scansRes.data);
        setChats(chatsRes.data);
      } catch (err) {
        console.error('Error loading dashboard data:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  const handleDownloadReport = async (scanId: string) => {
    setDownloadingId(scanId);
    try {
      const response = await api.get(`/api/v1/contracts/scan/${scanId}/export`, {
        responseType: 'blob'
      });
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `nyaya_compliance_report_${scanId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
    } catch (err) {
      alert('Error downloading report. Scan may still be processing.');
    } finally {
      setDownloadingId(null);
    }
  };

  const handleDeleteChat = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this chat session?')) return;
    
    try {
      await api.delete(`/api/v1/chat/sessions/${sessionId}`);
      // Refresh chats list
      setChats(prev => prev.filter(c => c.session_id !== sessionId));
      // Reload stats to update chat count
      const statsRes = await api.get('/api/v1/dashboard/stats');
      setStats(statsRes.data);
    } catch (err) {
      alert('Failed to delete chat session.');
    }
  };

  const formatDate = (dateString: string) => {
    try {
      const d = new Date(dateString);
      return d.toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' });
    } catch {
      return dateString;
    }
  };

  const getRelativeTime = (dateString: string) => {
    try {
      const d = new Date(dateString);
      const now = new Date();
      const diffMs = now.getTime() - d.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      if (diffMins < 1) return 'Just now';
      if (diffMins < 60) return `${diffMins} mins ago`;
      const diffHours = Math.floor(diffMins / 60);
      if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
      return formatDate(dateString);
    } catch {
      return dateString;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-page flex flex-col items-center justify-center text-primary">
        <Loader2 className="w-10 h-10 text-[var(--toxic-orange)] animate-spin mb-4" />
        <p className="font-display font-medium text-lg">Loading legal intelligence dashboard...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-page flex flex-col transition-all duration-300 pb-24">
      {/* Header */}
      <Header workspaceLabel="Workspace" />

      {/* ==================== MAIN CONTENT ==================== */}
      <main className="max-w-7xl mx-auto px-6 py-8 flex-1 w-full">
        {/* Welcome Section */}
        <div className="mb-8">
          <h2 className="font-display font-bold text-2xl md:text-3xl text-primary">
            Welcome back, {username.split('@')[0]}
          </h2>
          <p className="text-secondary mt-1">Here’s the latest intelligence on your contract portfolio.</p>
        </div>

        {/* Stats Widgets */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {/* 1. Contracts Ingested */}
          <div className="bg-surface border-kite rounded-lg p-5">
            <div className="flex items-center justify-between mb-4">
              <span className="text-xs font-medium text-secondary uppercase tracking-wider">Contracts Ingested</span>
              <FileText className="w-4 h-4 text-muted" />
            </div>
            <div className="flex items-baseline gap-2 mb-3">
              <span className="font-display font-bold text-3xl text-primary">
                {stats.total_contracts_scanned}
              </span>
              <span className="text-sm text-muted">/ 200 limit</span>
            </div>
            <div className="w-full h-1.5 rounded-full bg-[var(--black-kite-15)] overflow-hidden">
              <div
                className="h-full bg-[var(--toxic-orange)] rounded-full transition-all"
                style={{ width: `${Math.min((stats.total_contracts_scanned / 200) * 100, 100)}%` }}
              ></div>
            </div>
          </div>

          {/* 2. Total Risks Identified */}
          <div className="bg-surface border-kite rounded-lg p-5">
            <div className="flex items-center justify-between mb-4">
              <span className="text-xs font-medium text-secondary uppercase tracking-wider">Risks Identified</span>
              <AlertTriangle className="w-4 h-4 text-[var(--garnet)]" />
            </div>
            <div className="flex items-baseline gap-2 mb-3">
              <span className="font-display font-bold text-3xl" style={{ color: '#D32F2F' }}>
                {stats.total_risks_identified}
              </span>
              <span className="text-sm text-muted">total findings</span>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-muted">
              <TrendingUp className="w-3 h-3 text-safe-text" />
              <span>Monitored in real-time</span>
            </div>
          </div>

          {/* 3. Open RAG Chats */}
          <div className="bg-surface border-kite rounded-lg p-5">
            <div className="flex items-center justify-between mb-4">
              <span className="text-xs font-medium text-secondary uppercase tracking-wider">Open RAG Chats</span>
              <MessageSquare className="w-4 h-4 text-[var(--aqua-mist)]" />
            </div>
            <div className="flex items-baseline gap-2 mb-3">
              <span className="font-display font-bold text-3xl text-primary">{chats.length}</span>
              <span className="text-sm text-muted">active sessions</span>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-muted">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--safe-text)] animate-pulse"></span>
              <span>Fully cached in Redis</span>
            </div>
          </div>

          {/* 4. API Usage / Cost */}
          <div className="bg-surface border-kite rounded-lg p-5">
            <div className="flex items-center justify-between mb-4">
              <span className="text-xs font-medium text-secondary uppercase tracking-wider">API Usage / Cost</span>
              <IndianRupee className="w-4 h-4 text-muted" />
            </div>
            <div className="flex items-baseline gap-2 mb-3">
              <span className="font-display font-bold text-3xl text-primary">
                {stats.total_api_cost}
              </span>
            </div>
            <div className="inline-block px-2 py-1 rounded text-[10px] font-bold uppercase tracking-wider risk-safe">
              All Free Tiers
            </div>
          </div>
        </div>

        {/* Grid Layout: History Table & Sidebar */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Contract Ingestion History Table */}
          <div className="lg:col-span-2 bg-surface border-kite rounded-lg overflow-hidden flex flex-col justify-between">
            <div>
              <div className="p-5 border-kite-t flex items-center justify-between">
                <h3 className="font-display font-semibold text-lg text-primary">
                  Contract Ingestion History
                </h3>
                <button
                  onClick={() => router.push('/scan')}
                  className="text-xs font-semibold text-[var(--toxic-orange)] hover:underline flex items-center gap-1"
                >
                  <Plus className="w-3.5 h-3.5" /> Start New Scan
                </button>
              </div>
              <div className="overflow-x-auto">
                {scans.length === 0 ? (
                  <div className="p-8 text-center text-secondary">
                    <FileText className="w-10 h-10 mx-auto text-muted mb-2" />
                    <p className="text-sm font-medium">No contracts scanned yet.</p>
                    <p className="text-xs text-muted mt-1">Upload a PDF or DOCX contract to begin compliance auditing.</p>
                  </div>
                ) : (
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="border-b border-[var(--black-kite-15)]">
                        <th className="p-4 text-xs font-semibold text-muted uppercase tracking-wider">
                          Document Name
                        </th>
                        <th className="p-4 text-xs font-semibold text-muted uppercase tracking-wider hidden md:table-cell">
                          Clauses
                        </th>
                        <th className="p-4 text-xs font-semibold text-muted uppercase tracking-wider">
                          Status
                        </th>
                        <th className="p-4 text-xs font-semibold text-muted uppercase tracking-wider hidden md:table-cell">
                          Scan Date
                        </th>
                        <th className="p-4 text-xs font-semibold text-muted uppercase tracking-wider text-right">
                          Actions
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {scans.map((s) => (
                        <tr
                          key={s.scan_id}
                          onClick={() => router.push(`/scan?id=${s.scan_id}`)}
                          className="clause-item border-b border-[var(--black-kite-15)] cursor-pointer hover:bg-[var(--surface-hover)] transition-colors"
                        >
                          <td className="p-4">
                            <div className="font-medium text-primary text-sm">{s.contract_name}</div>
                            <div className="text-[10px] text-muted mt-0.5 font-mono">
                              ID: {s.scan_id.substring(0, 8)}
                            </div>
                          </td>
                          <td className="p-4 text-sm text-secondary hidden md:table-cell">
                            {s.clause_count || '-'}
                          </td>
                          <td className="p-4">
                            {s.status === 'processing' ? (
                              <span className="bg-yellow-100 dark:bg-yellow-950/40 text-yellow-800 dark:text-yellow-300 border border-yellow-300 dark:border-yellow-900 px-2.5 py-1 rounded text-[10px] font-bold uppercase tracking-wider flex items-center gap-1 w-fit animate-pulse">
                                Scanning
                              </span>
                            ) : s.status === 'failed' ? (
                              <span className="bg-red-100 dark:bg-red-950/40 text-red-700 dark:text-red-300 border border-red-300 dark:border-red-900 px-2.5 py-1 rounded text-[10px] font-bold uppercase tracking-wider flex items-center gap-1 w-fit">
                                Failed
                              </span>
                            ) : s.risk_level === 'high' ? (
                              <span className="bg-red-100 dark:bg-red-950/40 text-red-700 dark:text-red-300 border border-red-300 dark:border-red-900 px-2.5 py-1 rounded text-[10px] font-bold uppercase tracking-wider flex items-center gap-1 w-fit">
                                <AlertTriangle className="w-2.5 h-2.5" /> High Risk
                              </span>
                            ) : s.risk_level === 'medium' ? (
                              <span className="bg-yellow-100 dark:bg-yellow-950/40 text-yellow-700 dark:text-yellow-300 border border-yellow-300 dark:border-yellow-900 px-2.5 py-1 rounded text-[10px] font-bold uppercase tracking-wider flex items-center gap-1 w-fit">
                                <AlertCircle className="w-2.5 h-2.5" /> Med Risk
                              </span>
                            ) : (
                              <span className="risk-safe px-2.5 py-1 rounded text-[10px] font-bold uppercase tracking-wider flex items-center gap-1 w-fit">
                                <CheckCircle className="w-2.5 h-2.5" /> Compliant
                              </span>
                            )}
                          </td>
                          <td className="p-4 text-sm text-secondary hidden md:table-cell">
                            {formatDate(s.scan_date)}
                          </td>
                          <td className="p-4 text-right" onClick={(e) => e.stopPropagation()}>
                            <div className="flex items-center justify-end gap-3">
                              {s.status === 'complete' && (
                                <button
                                  onClick={() => handleDownloadReport(s.scan_id)}
                                  disabled={downloadingId === s.scan_id}
                                  className="text-xs font-medium text-[var(--toxic-orange)] hover:underline flex items-center gap-1 disabled:opacity-50"
                                >
                                  {downloadingId === s.scan_id ? (
                                    <Loader2 className="w-3 h-3 animate-spin" />
                                  ) : (
                                    'Download PDF'
                                  )}
                                </button>
                              )}
                              <button
                                onClick={() => router.push(`/scan?id=${s.scan_id}`)}
                                className="text-muted hover:text-primary"
                                title="View details"
                              >
                                <ExternalLink className="w-4 h-4" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          </div>

          {/* RAG Chat History Sidebar */}
          <div className="lg:col-span-1 bg-surface border-kite rounded-lg overflow-hidden h-fit flex flex-col justify-between">
            <div>
              <div className="p-5 border-kite-t flex items-center justify-between">
                <h3 className="font-display font-semibold text-lg text-primary">RAG Chat History</h3>
                <button
                  onClick={() => router.push('/chat')}
                  className="text-xs font-semibold text-[var(--toxic-orange)] hover:underline flex items-center gap-1"
                >
                  <Plus className="w-3.5 h-3.5" /> Start Chat
                </button>
              </div>
              <div className="flex flex-col">
                {chats.length === 0 ? (
                  <div className="p-8 text-center text-secondary">
                    <MessageSquare className="w-8 h-8 mx-auto text-muted mb-2" />
                    <p className="text-xs font-medium">No previous chats.</p>
                  </div>
                ) : (
                  chats.map((c) => (
                    <div
                      key={c.session_id}
                      onClick={() => router.push(`/chat?session_id=${c.session_id}`)}
                      className="clause-item border-b border-[var(--black-kite-15)] p-4 cursor-pointer hover:bg-[var(--surface-hover)] transition-colors"
                    >
                      <div className="flex items-start justify-between mb-2 gap-4">
                        <span className="text-[11px] font-mono text-muted">
                          {getRelativeTime(c.created_at)}
                        </span>
                        <button
                          onClick={(e) => handleDeleteChat(c.session_id, e)}
                          className="text-muted hover:text-[var(--garnet)] transition-colors p-1"
                          title="Delete Session"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                      <p className="text-sm font-medium text-primary mb-3 line-clamp-2">
                        {c.title || 'Untitled Session'}
                      </p>
                      <button
                        onClick={() => router.push(`/chat?session_id=${c.session_id}`)}
                        className="w-full px-3 py-1.5 border border-[var(--black-kite-15)] rounded text-xs font-medium text-secondary hover:bg-[var(--amazon-mist)] hover:text-primary transition-colors flex items-center justify-center gap-1.5"
                      >
                        <Play className="w-3 h-3 text-rose-gold fill-rose-gold" />
                        Resume Chat
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* ==================== FLOATING ACTION BUTTON ==================== */}
      <button
        onClick={() => router.push('/scan')}
        className="fixed bottom-6 right-6 bg-[var(--toxic-orange)] text-[#1A0A05] hover:bg-[#FF7855] shadow-lg rounded-full px-5 py-3.5 font-semibold text-sm flex items-center gap-2 transition-transform hover:scale-105 active:scale-95 z-40"
      >
        <Plus className="w-5 h-5" />
        <span>Upload New Contract</span>
      </button>
    </div>
  );
}
