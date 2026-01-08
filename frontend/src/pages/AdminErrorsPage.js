import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  AlertTriangle, AlertCircle, CheckCircle, Clock,
  RefreshCw, Filter, Search, Wrench, Eye, XCircle,
  Activity, Server, Database, Mail, Bot, TrendingUp
} from 'lucide-react';
import axios from 'axios';
import { toast } from 'react-toastify';
import DashboardLayout from '@/components/DashboardLayout';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const AdminErrorsPage = () => {
  const [errors, setErrors] = useState([]);
  const [stats, setStats] = useState({ total: 0, unresolved: 0, critical: 0 });
  const [systemHealth, setSystemHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    severity: '',
    category: '',
    resolved: ''
  });
  const [selectedError, setSelectedError] = useState(null);
  const [diagnosing, setDiagnosing] = useState(false);
  const [diagnosis, setDiagnosis] = useState(null);

  useEffect(() => {
    fetchErrors();
    fetchSystemHealth();
  }, [filters]);

  const fetchErrors = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const params = new URLSearchParams();
      if (filters.severity) params.append('severity', filters.severity);
      if (filters.category) params.append('category', filters.category);
      if (filters.resolved !== '') params.append('resolved', filters.resolved);

      const response = await axios.get(
        `${API_URL}/api/admin/errors?${params.toString()}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      setErrors(response.data.errors || []);
      setStats(response.data.stats || { total: 0, unresolved: 0, critical: 0 });
    } catch (err) {
      toast.error('Failed to load errors');
    } finally {
      setLoading(false);
    }
  };

  const fetchSystemHealth = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/api/admin/system-health`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSystemHealth(response.data);
    } catch (err) {
      console.error('Failed to fetch system health:', err);
    }
  };

  const handleDiagnose = async (error) => {
    setSelectedError(error);
    setDiagnosing(true);
    setDiagnosis(null);

    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(
        `${API_URL}/api/support-bot/diagnose`,
        {
          error_id: error.id,
          question: `Diagnose error: ${error.error_message}`,
          context: { endpoint: error.endpoint }
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      setDiagnosis(response.data);
    } catch (err) {
      toast.error('Failed to get AI diagnosis');
    } finally {
      setDiagnosing(false);
    }
  };

  const handleAutoFix = async (errorId) => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(
        `${API_URL}/api/support-bot/auto-fix/${errorId}`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );

      if (response.data.success) {
        toast.success('Auto-fix successful!');
        fetchErrors();
      } else {
        toast.warning(response.data.message);
      }
    } catch (err) {
      toast.error('Auto-fix failed');
    }
  };

  const handleResolve = async (errorId) => {
    try {
      const token = localStorage.getItem('token');
      await axios.put(
        `${API_URL}/api/admin/errors/${errorId}/resolve`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );

      toast.success('Error marked as resolved');
      fetchErrors();
      setSelectedError(null);
    } catch (err) {
      toast.error('Failed to resolve error');
    }
  };

  const getSeverityBadge = (severity) => {
    const styles = {
      critical: 'bg-red-100 text-red-700 border-red-200',
      high: 'bg-orange-100 text-orange-700 border-orange-200',
      medium: 'bg-yellow-100 text-yellow-700 border-yellow-200',
      low: 'bg-green-100 text-green-700 border-green-200'
    };
    return styles[severity] || styles.medium;
  };

  const getHealthColor = (status) => {
    switch (status) {
      case 'healthy': return 'text-green-500';
      case 'warning': return 'text-yellow-500';
      case 'critical': return 'text-red-500';
      case 'configured': return 'text-green-500';
      case 'not_configured': return 'text-gray-400';
      default: return 'text-gray-500';
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  return (
    <DashboardLayout>
      <div className="p-4 lg:p-6">
        {/* Header */}
        <div className="mb-6 lg:mb-8">
          <h1 className="text-2xl lg:text-4xl font-bold text-foreground mb-1 lg:mb-2">
            System Errors & Health
          </h1>
          <p className="text-sm lg:text-base text-secondary">
            Monitor system health and manage errors with AI-powered diagnostics
          </p>
        </div>

        {/* System Health Cards */}
        {systemHealth && (
          <div className="grid grid-cols-2 lg:grid-cols-6 gap-3 lg:gap-4 mb-6">
            <div className={`col-span-2 lg:col-span-1 bg-white p-4 rounded-xl border border-border ${
              systemHealth.overall === 'critical' ? 'border-red-300 bg-red-50' : ''
            }`}>
              <div className="flex items-center gap-2 mb-2">
                <Activity className={`w-5 h-5 ${getHealthColor(systemHealth.overall)}`} />
                <span className="text-sm text-secondary">Overall</span>
              </div>
              <p className={`text-lg font-bold capitalize ${getHealthColor(systemHealth.overall)}`}>
                {systemHealth.overall}
              </p>
            </div>

            <div className="bg-white p-4 rounded-xl border border-border">
              <div className="flex items-center gap-2 mb-2">
                <Database className={`w-5 h-5 ${getHealthColor(systemHealth.services?.database)}`} />
                <span className="text-sm text-secondary">Database</span>
              </div>
              <p className={`text-lg font-bold capitalize ${getHealthColor(systemHealth.services?.database)}`}>
                {systemHealth.services?.database}
              </p>
            </div>

            <div className="bg-white p-4 rounded-xl border border-border">
              <div className="flex items-center gap-2 mb-2">
                <Mail className={`w-5 h-5 ${getHealthColor(systemHealth.services?.resend_email)}`} />
                <span className="text-sm text-secondary">Email</span>
              </div>
              <p className={`text-lg font-bold capitalize ${getHealthColor(systemHealth.services?.resend_email)}`}>
                {systemHealth.services?.resend_email?.replace('_', ' ')}
              </p>
            </div>

            <div className="bg-white p-4 rounded-xl border border-border">
              <div className="flex items-center gap-2 mb-2">
                <Bot className={`w-5 h-5 ${getHealthColor(systemHealth.services?.ai_diagnosis)}`} />
                <span className="text-sm text-secondary">AI Support</span>
              </div>
              <p className={`text-lg font-bold capitalize ${getHealthColor(systemHealth.services?.ai_diagnosis)}`}>
                {systemHealth.services?.ai_diagnosis?.replace('_', ' ')}
              </p>
            </div>

            <div className="bg-white p-4 rounded-xl border border-border">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle className="w-5 h-5 text-red-500" />
                <span className="text-sm text-secondary">Critical (24h)</span>
              </div>
              <p className="text-lg font-bold text-red-600">
                {systemHealth.critical_errors_24h}
              </p>
            </div>

            <div className="bg-white p-4 rounded-xl border border-border">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="w-5 h-5 text-orange-500" />
                <span className="text-sm text-secondary">Total (24h)</span>
              </div>
              <p className="text-lg font-bold text-orange-600">
                {systemHealth.recent_errors_24h}
              </p>
            </div>
          </div>
        )}

        {/* Stats Overview */}
        <div className="grid grid-cols-3 gap-3 lg:gap-4 mb-6">
          <div className="bg-white p-4 rounded-xl border border-border">
            <p className="text-2xl lg:text-3xl font-bold text-foreground">{stats.total}</p>
            <p className="text-sm text-secondary">Total Errors</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-border">
            <p className="text-2xl lg:text-3xl font-bold text-orange-600">{stats.unresolved}</p>
            <p className="text-sm text-secondary">Unresolved</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-border">
            <p className="text-2xl lg:text-3xl font-bold text-red-600">{stats.critical}</p>
            <p className="text-sm text-secondary">Critical</p>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-3 mb-6">
          <select
            value={filters.severity}
            onChange={(e) => setFilters(prev => ({ ...prev, severity: e.target.value }))}
            className="px-4 py-2 border border-border rounded-lg text-sm bg-white"
          >
            <option value="">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>

          <select
            value={filters.category}
            onChange={(e) => setFilters(prev => ({ ...prev, category: e.target.value }))}
            className="px-4 py-2 border border-border rounded-lg text-sm bg-white"
          >
            <option value="">All Categories</option>
            <option value="authentication">Authentication</option>
            <option value="database">Database</option>
            <option value="file_upload">File Upload</option>
            <option value="network">Network</option>
            <option value="system">System</option>
          </select>

          <select
            value={filters.resolved}
            onChange={(e) => setFilters(prev => ({ ...prev, resolved: e.target.value }))}
            className="px-4 py-2 border border-border rounded-lg text-sm bg-white"
          >
            <option value="">All Status</option>
            <option value="false">Unresolved</option>
            <option value="true">Resolved</option>
          </select>

          <button
            onClick={fetchErrors}
            className="px-4 py-2 bg-primary text-white rounded-lg text-sm flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>

        {/* Errors List */}
        <div className="bg-white rounded-xl border border-border overflow-hidden">
          {loading ? (
            <div className="p-8 text-center">
              <RefreshCw className="w-8 h-8 animate-spin text-primary mx-auto mb-3" />
              <p className="text-secondary">Loading errors...</p>
            </div>
          ) : errors.length === 0 ? (
            <div className="p-8 text-center">
              <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-3" />
              <p className="text-secondary">No errors found</p>
            </div>
          ) : (
            <div className="divide-y divide-border">
              {errors.map((error) => (
                <div key={error.id} className="p-4 hover:bg-slate-50 transition-colors">
                  <div className="flex flex-col lg:flex-row lg:items-center gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2 mb-2">
                        <span className={`px-2 py-0.5 text-xs font-medium rounded-full border ${getSeverityBadge(error.severity)}`}>
                          {error.severity}
                        </span>
                        <span className="px-2 py-0.5 text-xs bg-slate-100 text-slate-600 rounded-full">
                          {error.category}
                        </span>
                        {error.resolved && (
                          <span className="px-2 py-0.5 text-xs bg-green-100 text-green-700 rounded-full">
                            Resolved
                          </span>
                        )}
                      </div>
                      <p className="font-medium text-foreground truncate">{error.error_type}</p>
                      <p className="text-sm text-secondary truncate">{error.error_message}</p>
                      <div className="flex items-center gap-4 mt-2 text-xs text-secondary">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {formatDate(error.created_at)}
                        </span>
                        {error.endpoint && (
                          <span className="truncate">Endpoint: {error.endpoint}</span>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleDiagnose(error)}
                        className="px-3 py-1.5 bg-blue-50 text-blue-600 rounded-lg text-sm flex items-center gap-1 hover:bg-blue-100"
                      >
                        <Bot className="w-4 h-4" />
                        Diagnose
                      </button>
                      {!error.resolved && (
                        <>
                          <button
                            onClick={() => handleAutoFix(error.id)}
                            className="px-3 py-1.5 bg-orange-50 text-orange-600 rounded-lg text-sm flex items-center gap-1 hover:bg-orange-100"
                          >
                            <Wrench className="w-4 h-4" />
                            Auto-Fix
                          </button>
                          <button
                            onClick={() => handleResolve(error.id)}
                            className="px-3 py-1.5 bg-green-50 text-green-600 rounded-lg text-sm flex items-center gap-1 hover:bg-green-100"
                          >
                            <CheckCircle className="w-4 h-4" />
                            Resolve
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* AI Diagnosis Modal */}
        {selectedError && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="bg-white rounded-2xl shadow-xl max-w-2xl w-full max-h-[80vh] overflow-y-auto"
            >
              <div className="p-6 border-b border-border flex items-center justify-between">
                <h3 className="text-lg font-semibold">AI Diagnosis</h3>
                <button
                  onClick={() => { setSelectedError(null); setDiagnosis(null); }}
                  className="p-2 hover:bg-slate-100 rounded-lg"
                >
                  <XCircle className="w-5 h-5 text-secondary" />
                </button>
              </div>

              <div className="p-6">
                {diagnosing ? (
                  <div className="text-center py-8">
                    <RefreshCw className="w-8 h-8 animate-spin text-primary mx-auto mb-3" />
                    <p className="text-secondary">AI is analyzing the error...</p>
                  </div>
                ) : diagnosis ? (
                  <div className="space-y-4">
                    <div>
                      <h4 className="font-medium text-foreground mb-2">Diagnosis</h4>
                      <p className="text-secondary">{diagnosis.diagnosis}</p>
                    </div>

                    {diagnosis.root_cause && (
                      <div>
                        <h4 className="font-medium text-foreground mb-2">Root Cause</h4>
                        <p className="text-secondary">{diagnosis.root_cause}</p>
                      </div>
                    )}

                    {diagnosis.fix_steps?.length > 0 && (
                      <div>
                        <h4 className="font-medium text-foreground mb-2">Fix Steps</h4>
                        <ol className="space-y-2">
                          {diagnosis.fix_steps.map((step, i) => (
                            <li key={i} className="flex items-start gap-2">
                              <span className="flex-shrink-0 w-6 h-6 bg-primary/10 text-primary rounded-full flex items-center justify-center text-sm font-medium">
                                {i + 1}
                              </span>
                              <span className="text-secondary">{step}</span>
                            </li>
                          ))}
                        </ol>
                      </div>
                    )}

                    {diagnosis.prevention && (
                      <div>
                        <h4 className="font-medium text-foreground mb-2">Prevention</h4>
                        <p className="text-secondary">{diagnosis.prevention}</p>
                      </div>
                    )}

                    {diagnosis.can_auto_fix && (
                      <div className="pt-4 border-t border-border">
                        <button
                          onClick={() => handleAutoFix(selectedError.id)}
                          className="w-full py-3 bg-primary text-white rounded-lg font-medium flex items-center justify-center gap-2 hover:bg-primary/90"
                        >
                          <Wrench className="w-5 h-5" />
                          Apply Auto-Fix
                        </button>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <Bot className="w-12 h-12 text-secondary/30 mx-auto mb-3" />
                    <p className="text-secondary">Click Diagnose to analyze this error</p>
                  </div>
                )}
              </div>
            </motion.div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
};

export default AdminErrorsPage;
