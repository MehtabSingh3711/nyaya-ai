'use client';

import React, { useEffect, useState, useRef } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Header from '@/components/Header';
import { api } from '@/lib/api';
import {
  UploadCloud,
  FileText,
  AlertTriangle,
  AlertCircle,
  CheckCircle,
  FileDown,
  ChevronRight,
  ChevronLeft,
  Loader2,
  Scale,
  Compass,
  ArrowLeft,
  Clock,
  ExternalLink,
  BookOpen
} from 'lucide-react';

interface Precedent {
  case_name: string;
  citation: string;
  core_holding: string;
}

interface RiskFinding {
  clause_number: string;
  clause_text: string;
  page: number;
  clause_type: string;
  risk_level: 'high' | 'medium' | 'low';
  conflicting_act: string;
  conflicting_section: string;
  conflicting_law_quote: string;
  explanation: string;
  recommended_action: string;
  confidence: number;
  relevant_precedents: Precedent[];
}

interface ScanResult {
  scan_id: string;
  status: string;
  contract_name: string;
  clause_count: number;
  risk_level: 'high' | 'medium' | 'low' | null;
  scan_date: string;
  results: {
    findings: RiskFinding[];
    total_clauses_scanned: number;
    scan_confidence: number;
    status: string;
    message: string;
  } | null;
}

export default function ContractScannerPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryScanId = searchParams.get('id');

  // Scanner States
  const [scanRecord, setScanRecord] = useState<ScanResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');
  
  // Workstation active selection state
  const [activeIndex, setActiveIndex] = useState<number>(0);
  const [riskFilter, setRiskFilter] = useState<'all' | 'high' | 'medium' | 'safe'>('all');
  const [dragActive, setDragActive] = useState(false);
  const [exporting, setExporting] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load existing scan from URL query
  const loadScanDetails = async (scanId: string) => {
    setLoading(true);
    setStatusMessage('Loading scan records...');
    try {
      const res = await api.get(`/api/v1/contracts/scan/${scanId}`);
      setScanRecord(res.data);
      if (res.data.status === 'processing') {
        startPolling(scanId);
      }
    } catch (err) {
      console.error('Error loading scan details:', err);
      alert('Could not fetch scan details. Returning to scan page.');
      router.push('/scan');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (queryScanId) {
      loadScanDetails(queryScanId);
    } else {
      setScanRecord(null);
    }
  }, [queryScanId]);

  // Polling mechanism
  const startPolling = (scanId: string) => {
    setStatusMessage('Auditing contract clauses against Central Acts...');
    const interval = setInterval(async () => {
      try {
        const res = await api.get(`/api/v1/contracts/scan/${scanId}`);
        const data = res.data as ScanResult;
        
        if (data.status === 'complete') {
          clearInterval(interval);
          setScanRecord(data);
          setLoading(false);
          setStatusMessage('');
        } else if (data.status === 'failed') {
          clearInterval(interval);
          setScanRecord(data);
          setLoading(false);
          alert('Scanning failed. Document format may be unsupported.');
        }
      } catch (err) {
        clearInterval(interval);
        setLoading(false);
        alert('An error occurred during status updates.');
      }
    }, 2000);
  };

  // Drag and drop handlers
  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      await uploadFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      await uploadFile(e.target.files[0]);
    }
  };

  const uploadFile = async (file: File) => {
    // Validate extension
    const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    if (ext !== '.pdf' && ext !== '.docx') {
      alert('Invalid file format. Only PDF and DOCX are supported.');
      return;
    }

    // Validate size (10MB)
    if (file.size > 10 * 1024 * 1024) {
      alert('File size exceeds the 10MB limit.');
      return;
    }

    setLoading(true);
    setStatusMessage('Uploading document and extracting clauses...');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await api.post('/api/v1/contracts/scan', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      const { scan_id } = res.data;
      
      // Update query params to load scan details
      window.history.pushState(null, '', `/scan?id=${scan_id}`);
      startPolling(scan_id);
    } catch (err: any) {
      setLoading(false);
      const detail = err.response?.data?.detail;
      alert(typeof detail === 'string' ? detail : 'Failed to start contract scan.');
    }
  };

  const handleExport = async () => {
    if (!scanRecord || scanRecord.status !== 'complete') return;
    setExporting(true);
    try {
      const response = await api.get(`/api/v1/contracts/scan/${scanRecord.scan_id}/export`, {
        responseType: 'blob'
      });
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `nyaya_compliance_report_${scanRecord.scan_id}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
    } catch (err) {
      alert('Error exporting PDF compliance report.');
    } finally {
      setExporting(false);
    }
  };

  // Filtering findings
  const getFilteredFindings = () => {
    if (!scanRecord || !scanRecord.results) return [];
    const findings = scanRecord.results.findings || [];
    if (riskFilter === 'all') return findings;
    if (riskFilter === 'safe') return []; // Live results only contain risks
    return findings.filter(f => f.risk_level === riskFilter);
  };

  const filteredFindings = getFilteredFindings();
  const activeFinding = filteredFindings[activeIndex];

  // Adjust active index if it exceeds array length after changing filters
  useEffect(() => {
    setActiveIndex(0);
  }, [riskFilter]);

  if (loading && !scanRecord) {
    return (
      <div className="min-h-screen bg-page flex flex-col items-center justify-center text-primary">
        <Loader2 className="w-12 h-12 text-[var(--toxic-orange)] animate-spin mb-4" />
        <p className="font-display font-medium text-lg">{statusMessage}</p>
        <p className="text-xs text-muted mt-2">This may take up to 30 seconds for long files.</p>
      </div>
    );
  }

  // Active Ingestion / Scanning state
  if (scanRecord && scanRecord.status === 'processing') {
    return (
      <div className="min-h-screen bg-page flex flex-col transition-all duration-300">
        <Header workspaceLabel="Mode 1: Compliance Scan" />
        <main className="max-w-md mx-auto px-6 py-24 flex-1 flex flex-col items-center justify-center text-center">
          <Loader2 className="w-12 h-12 text-[var(--toxic-orange)] animate-spin mb-4" />
          <h2 className="font-display font-bold text-xl text-primary">Ingestion & Analysis in progress</h2>
          <p className="text-sm text-secondary mt-2">Checking terms against 33,000+ statutory sections and court precedents.</p>
          <div className="w-full bg-[var(--black-kite-15)] h-1 rounded-full overflow-hidden mt-6">
            <div className="bg-[var(--toxic-orange)] h-full w-2/3 rounded-full animate-pulse"></div>
          </div>
          <span className="text-[10px] text-muted font-mono uppercase tracking-wider mt-4">
            Document ID: {scanRecord.scan_id.substring(0, 8)}
          </span>
        </main>
      </div>
    );
  }

  // UPLOAD SCREEN (Initial state)
  if (!scanRecord) {
    return (
      <div className="min-h-screen bg-page flex flex-col transition-all duration-300">
        <Header workspaceLabel="Mode 1: Compliance Scan" />
        
        <main className="max-w-4xl mx-auto px-6 py-12 flex-1 flex flex-col justify-center w-full">
          <div className="text-center mb-8">
            <h2 className="font-display font-bold text-3xl text-primary">Upload Legal Contract</h2>
            <p className="text-secondary mt-2">Scan NDA, MSA, Employment, or MSME vendor agreements for statutory risks.</p>
          </div>

          <div
            onDragEnter={handleDrag}
            onDragOver={handleDrag}
            onDragLeave={handleDrag}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`bg-surface border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all flex flex-col items-center justify-center ${
              dragActive ? 'border-toxic-orange bg-[var(--surface-hover)]' : 'border-[var(--black-kite-15)] hover:border-muted-copper'
            }`}
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept=".pdf,.docx"
              className="hidden"
            />
            <UploadCloud className="w-16 h-16 text-rose-gold mb-6 animate-pulse" />
            <h3 className="font-display font-semibold text-lg text-primary mb-1">
              Drag & drop your contract here
            </h3>
            <p className="text-xs text-muted mb-6">PDF or DOCX documents up to 10MB</p>
            <button type="button" className="btn-primary w-auto px-6 py-2.5">
              Select Document
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-8">
            <div className="bg-surface border-kite p-5 rounded-lg flex gap-3">
              <CheckCircle className="w-5 h-5 text-safe-text mt-0.5" />
              <div>
                <h4 className="text-sm font-semibold text-primary">Automatic Scan</h4>
                <p className="text-xs text-secondary mt-1">
                  Extracts clauses and flags void agreements or MSME payment violations instantly.
                </p>
              </div>
            </div>
            <div className="bg-surface border-kite p-5 rounded-lg flex gap-3">
              <CheckCircle className="w-5 h-5 text-safe-text mt-0.5" />
              <div>
                <h4 className="text-sm font-semibold text-primary">Landmark Precedents</h4>
                <p className="text-xs text-secondary mt-1">
                  Cross-references 100 landmark rulings (e.g. Century Spinning) to check enforceability.
                </p>
              </div>
            </div>
          </div>
        </main>
      </div>
    );
  }

  // SCAN WORKSTATION SCREEN (Complete scan results)
  return (
    <div className="min-h-screen bg-page flex flex-col transition-all duration-300 h-screen overflow-hidden">
      {/* Header */}
      <Header workspaceLabel="Mode 1: Compliance Scan" />

      {/* Sub Bar */}
      <div className="border-kite-b bg-surface px-6 h-[52px] flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-5 text-xs">
          <button 
            onClick={() => router.push('/dashboard')}
            className="flex items-center gap-1.5 text-secondary hover:text-primary mr-2"
          >
            <ArrowLeft className="w-4 h-4" /> <span className="hidden sm:inline">Dashboard</span>
          </button>
          
          <div className="h-4 w-px bg-[var(--black-kite-15)] hidden sm:block"></div>

          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-safe-text animate-pulse"></span>
            <span className="font-semibold text-primary truncate max-w-[200px]" title={scanRecord.contract_name}>
              {scanRecord.contract_name}
            </span>
            <span className="text-muted">·</span>
            <span className="text-secondary uppercase text-[10px] font-bold">
              {scanRecord.status.toUpperCase()}
            </span>
          </div>

          <div className="hidden md:flex items-center gap-1.5 text-muted">
            <FileText className="w-3.5 h-3.5" />
            <span className="font-mono">{scanRecord.clause_count || 0} Clauses Scanned</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {scanRecord.status === 'complete' && (
            <button
              onClick={handleExport}
              disabled={exporting}
              className="btn-primary px-3 py-1.5 rounded text-xs w-auto flex items-center gap-1.5 disabled:opacity-50"
            >
              {exporting ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <FileDown className="w-3.5 h-3.5" />
              )}
              <span>Export Report</span>
            </button>
          )}
        </div>
      </div>

      {/* ==================== WORKSTATION WORKSPACE GRID ==================== */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-[300px_1fr_360px] overflow-hidden">
        
        {/* ==================== LEFT: CLAUSE NAVIGATOR ==================== */}
        <aside className="border-r border-[var(--black-kite-15)] bg-surface flex flex-col overflow-hidden">
          <div className="p-4 border-b border-[var(--black-kite-15)] flex-shrink-0">
            <h3 className="font-display font-semibold text-sm text-primary mb-3">
              Clause Navigator
            </h3>
            
            {/* Filter chips */}
            <div className="flex items-center gap-1 overflow-x-auto pb-1">
              <button
                onClick={() => setRiskFilter('all')}
                className={`px-2 py-1 text-[10px] font-semibold rounded whitespace-nowrap ${
                  riskFilter === 'all'
                    ? 'bg-[var(--toxic-orange)] text-[#1A0A05]'
                    : 'bg-page border border-[var(--black-kite-15)] text-secondary hover:text-primary'
                }`}
              >
                All · {scanRecord.results?.findings.length || 0}
              </button>
              <button
                onClick={() => setRiskFilter('high')}
                className={`px-2 py-1 text-[10px] font-medium rounded whitespace-nowrap flex items-center gap-1 ${
                  riskFilter === 'high'
                    ? 'bg-red-700 text-white'
                    : 'bg-page border border-[var(--black-kite-15)] text-secondary hover:text-primary'
                }`}
              >
                <span className="w-1.5 h-1.5 rounded-full bg-red-600"></span>
                High
              </button>
              <button
                onClick={() => setRiskFilter('medium')}
                className={`px-2 py-1 text-[10px] font-medium rounded whitespace-nowrap flex items-center gap-1 ${
                  riskFilter === 'medium'
                    ? 'bg-yellow-600 text-white'
                    : 'bg-page border border-[var(--black-kite-15)] text-secondary hover:text-primary'
                }`}
              >
                <span className="w-1.5 h-1.5 rounded-full bg-yellow-500"></span>
                Med
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto">
            {filteredFindings.length === 0 ? (
              <div className="p-6 text-center text-secondary">
                <CheckCircle className="w-8 h-8 text-safe-text mx-auto mb-2" />
                <p className="text-xs font-semibold">No active risks matched.</p>
                <p className="text-[10px] text-muted mt-1">This clause selection is clean.</p>
              </div>
            ) : (
              filteredFindings.map((f, idx) => (
                <div
                  key={idx}
                  onClick={() => setActiveIndex(idx)}
                  className={`p-4 border-b border-[var(--black-kite-15)] cursor-pointer transition-colors ${
                    activeIndex === idx ? 'bg-[var(--amazon-mist)]/50 border-r-2 border-r-[var(--rose-gold)]' : 'hover:bg-[var(--surface-hover)]'
                  }`}
                >
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-[10px] font-mono text-muted uppercase">
                      Clause {f.clause_number} · Page {f.page}
                    </span>
                    <span
                      className={`px-1.5 py-0.5 rounded text-[8px] font-bold uppercase tracking-wider ${
                        f.risk_level === 'high' ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'
                      }`}
                    >
                      {f.risk_level}
                    </span>
                  </div>
                  <p className="text-xs font-medium text-primary line-clamp-2">
                    {f.clause_text}
                  </p>
                </div>
              ))
            )}
          </div>
        </aside>

        {/* ==================== CENTER: CLAUSE TEXT PREVIEW ==================== */}
        <section className="bg-page flex flex-col overflow-hidden p-6">
          {activeFinding ? (
            <div className="flex-1 flex flex-col justify-between bg-surface border-kite rounded-xl p-6 overflow-hidden">
              <div className="overflow-y-auto">
                <div className="flex items-center justify-between mb-4 pb-4 border-b border-[var(--black-kite-15)]">
                  <div>
                    <h3 className="font-display font-semibold text-lg text-primary">
                      Clause {activeFinding.clause_number} (Page {activeFinding.page})
                    </h3>
                    <p className="text-xs text-muted uppercase mt-0.5 font-mono">
                      Category: {activeFinding.clause_type}
                    </p>
                  </div>
                  <span
                    className={`px-2.5 py-1 rounded text-xs font-bold uppercase tracking-wider ${
                      activeFinding.risk_level === 'high' ? 'risk-high' : 'risk-medium'
                    }`}
                  >
                    {activeFinding.risk_level} Risk Identified
                  </span>
                </div>
                
                <h4 className="text-xs font-bold uppercase tracking-wider text-muted mb-2">
                  Verbatim Clause Text
                </h4>
                <div className="bg-page border-kite p-4 rounded-md mb-6">
                  <p className="text-sm font-medium text-primary leading-relaxed whitespace-pre-line">
                    &quot;{activeFinding.clause_text}&quot;
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center bg-surface border-kite rounded-xl p-6 text-center">
              <CheckCircle className="w-16 h-16 text-safe-text mb-4 animate-bounce" />
              <h3 className="font-display font-bold text-xl text-primary">
                Contract Ingestion Clean
              </h3>
              <p className="text-sm text-secondary mt-1 max-w-sm mx-auto leading-relaxed">
                No active statutory compliance risks matched the current filter. The clauses operate in alignment with Central Acts.
              </p>
            </div>
          )}
        </section>

        {/* ==================== RIGHT: STATUTORY ANALYSIS & PRECEDENTS ==================== */}
        <aside className="border-l border-[var(--black-kite-15)] bg-surface flex flex-col overflow-hidden">
          {activeFinding ? (
            <div className="flex-1 overflow-y-auto p-5 space-y-6">
              {/* Conflicting Statute card */}
              <div className="bg-page border border-red-200 dark:border-red-950 p-4 rounded-lg">
                <div className="flex items-center gap-1.5 mb-3 text-red-600 dark:text-red-400">
                  <Scale className="w-4 h-4" />
                  <span className="text-[11px] font-bold uppercase tracking-wider font-mono">
                    Conflicting Law
                  </span>
                </div>
                <h4 className="font-display font-semibold text-sm text-primary mb-1">
                  {activeFinding.conflicting_act}
                </h4>
                <p className="text-xs font-semibold text-rose-gold mb-3">
                  Section {activeFinding.conflicting_section}
                </p>
                <div className="border-l-2 border-red-300 dark:border-red-900 pl-3">
                  <p className="text-[11px] text-secondary leading-relaxed italic">
                    &quot;{activeFinding.conflicting_law_quote}&quot;
                  </p>
                </div>
              </div>

              {/* Legal explanation */}
              <div>
                <h4 className="text-[10px] font-bold uppercase tracking-wider text-muted mb-2">
                  Compliance Opinion
                </h4>
                <p className="text-xs text-secondary leading-relaxed bg-page p-3.5 rounded border border-[var(--black-kite-15)]">
                  {activeFinding.explanation}
                </p>
              </div>

              {/* Negotiation advice */}
              <div>
                <h4 className="text-[10px] font-bold uppercase tracking-wider text-muted mb-2">
                  Actionable Advice
                </h4>
                <p className="text-xs text-primary leading-relaxed bg-safe-bg/30 text-safe-text border border-safe-bg/60 p-3.5 rounded">
                  {activeFinding.recommended_action}
                </p>
              </div>

              {/* Supporting landmark precedents */}
              <div>
                <div className="flex items-center gap-1.5 mb-3">
                  <BookOpen className="w-4 h-4 text-rose-gold" />
                  <h4 className="text-[10px] font-bold uppercase tracking-wider text-muted">
                    Supporting Landmark Precedents
                  </h4>
                </div>
                {activeFinding.relevant_precedents && activeFinding.relevant_precedents.length > 0 ? (
                  <div className="space-y-3">
                    {activeFinding.relevant_precedents.map((prec, pIdx) => (
                      <div
                        key={pIdx}
                        className="bg-page border-kite p-3 rounded-lg flex flex-col"
                      >
                        <span className="text-xs font-bold text-primary mb-0.5">
                          {prec.case_name}
                        </span>
                        <span className="text-[9px] font-mono text-[var(--rose-gold)] mb-2 block">
                          {prec.citation}
                        </span>
                        <p className="text-[11px] text-secondary leading-relaxed italic pl-2 border-l border-[var(--black-kite-15)]">
                          &quot;{prec.core_holding}&quot;
                        </p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-4 bg-page rounded border border-[var(--black-kite-15)]">
                    <p className="text-[10px] text-muted italic">
                      No case precedents found matching this statutory section.
                    </p>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center p-6 text-center text-muted">
              <Compass className="w-10 h-10 mb-2 opacity-40 block mx-auto" />
              <p className="text-xs">No active risk selected.</p>
              <p className="text-[10px] opacity-75 mt-1">Choose a flagged clause from the navigator to view statutory arguments.</p>
            </div>
          )}
        </aside>

      </div>
    </div>
  );
}
