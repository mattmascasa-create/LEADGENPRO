import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Mail, Send, Eye, MousePointer, MessageSquare, TrendingUp,
  Calendar, Users, Target, ChevronRight, Plus, Play, Pause,
  BarChart3, RefreshCw, Loader2, CheckCircle, AlertTriangle,
  Clock, ArrowRight, Trash2, Edit, Copy
} from 'lucide-react';
import axios from 'axios';
import { toast } from 'react-toastify';
import { format } from 'date-fns';
import DashboardLayout from '@/components/DashboardLayout';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, PieChart, Pie, Cell, Legend, AreaChart, Area
} from 'recharts';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6'];

const EmailAnalyticsPage = () => {
  const [activeTab, setActiveTab] = useState('analytics');
  const [stats, setStats] = useState(null);
  const [sequences, setSequences] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedSequence, setSelectedSequence] = useState(null);
  const [showSequenceModal, setShowSequenceModal] = useState(false);
  const [timeRange, setTimeRange] = useState(30);

  const getAuthHeaders = () => ({
    Authorization: `Bearer ${localStorage.getItem('token')}`
  });

  useEffect(() => {
    fetchData();
  }, [timeRange]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [statsRes, sequencesRes] = await Promise.all([
        axios.get(`${API_URL}/api/email/tracking/stats?days=${timeRange}`, { headers: getAuthHeaders() }),
        axios.get(`${API_URL}/api/sequences`, { headers: getAuthHeaders() })
      ]);
      
      setStats(statsRes.data);
      setSequences(sequencesRes.data);
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('Failed to load email analytics');
    } finally {
      setLoading(false);
    }
  };

  const formatPercent = (value) => `${value}%`;

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-96">
          <RefreshCw className="w-8 h-8 animate-spin text-primary" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="p-4 lg:p-6">
        {/* Header */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl lg:text-4xl font-bold text-foreground mb-1 flex items-center gap-3">
              <Mail className="w-8 h-8 text-primary" />
              Email Analytics
            </h1>
            <p className="text-sm lg:text-base text-secondary">
              Track opens, clicks, and replies across all your campaigns
            </p>
          </div>
          
          <div className="flex items-center gap-3">
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(Number(e.target.value))}
              className="px-4 py-2 border border-border rounded-lg bg-white"
            >
              <option value={7}>Last 7 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
            </select>
            <button
              onClick={fetchData}
              className="p-2 hover:bg-slate-100 rounded-lg"
            >
              <RefreshCw className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {[
            { id: 'analytics', label: 'Analytics', icon: BarChart3 },
            { id: 'sequences', label: 'Sequences', icon: ArrowRight },
            { id: 'recent', label: 'Recent Emails', icon: Mail }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium whitespace-nowrap transition-colors ${
                activeTab === tab.id
                  ? 'bg-primary text-white'
                  : 'bg-white border border-border hover:bg-slate-50'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Analytics Tab */}
        {activeTab === 'analytics' && stats && (
          <div className="space-y-6">
            {/* Summary Stats */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-white p-5 rounded-xl border border-border"
              >
                <div className="flex items-center gap-3 mb-2">
                  <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                    <Send className="w-5 h-5 text-blue-600" />
                  </div>
                </div>
                <p className="text-2xl font-bold text-foreground">{stats.summary.total_sent}</p>
                <p className="text-sm text-secondary">Emails Sent</p>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="bg-white p-5 rounded-xl border border-border"
              >
                <div className="flex items-center gap-3 mb-2">
                  <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                    <Eye className="w-5 h-5 text-green-600" />
                  </div>
                </div>
                <p className="text-2xl font-bold text-foreground">{stats.summary.open_rate}%</p>
                <p className="text-sm text-secondary">Open Rate</p>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="bg-white p-5 rounded-xl border border-border"
              >
                <div className="flex items-center gap-3 mb-2">
                  <div className="w-10 h-10 bg-yellow-100 rounded-lg flex items-center justify-center">
                    <MousePointer className="w-5 h-5 text-yellow-600" />
                  </div>
                </div>
                <p className="text-2xl font-bold text-foreground">{stats.summary.click_rate}%</p>
                <p className="text-sm text-secondary">Click Rate</p>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="bg-white p-5 rounded-xl border border-border"
              >
                <div className="flex items-center gap-3 mb-2">
                  <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                    <MessageSquare className="w-5 h-5 text-purple-600" />
                  </div>
                </div>
                <p className="text-2xl font-bold text-foreground">{stats.summary.reply_rate}%</p>
                <p className="text-sm text-secondary">Reply Rate</p>
              </motion.div>
            </div>

            {/* Charts */}
            <div className="grid lg:grid-cols-2 gap-6">
              {/* Daily Trend */}
              <div className="bg-white p-6 rounded-xl border border-border">
                <h3 className="font-semibold mb-4">Email Activity Trend</h3>
                <ResponsiveContainer width="100%" height={250}>
                  <AreaChart data={stats.daily_breakdown}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                    <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Legend />
                    <Area type="monotone" dataKey="sent" stackId="1" stroke="#3B82F6" fill="#3B82F6" fillOpacity={0.6} name="Sent" />
                    <Area type="monotone" dataKey="opened" stackId="2" stroke="#10B981" fill="#10B981" fillOpacity={0.6} name="Opened" />
                    <Area type="monotone" dataKey="clicked" stackId="3" stroke="#F59E0B" fill="#F59E0B" fillOpacity={0.6} name="Clicked" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>

              {/* Funnel */}
              <div className="bg-white p-6 rounded-xl border border-border">
                <h3 className="font-semibold mb-4">Email Funnel</h3>
                <div className="space-y-4">
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span>Sent</span>
                      <span className="font-medium">{stats.summary.total_sent}</span>
                    </div>
                    <div className="h-8 bg-blue-500 rounded-lg" style={{ width: '100%' }} />
                  </div>
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span>Opened</span>
                      <span className="font-medium">{stats.summary.total_opened} ({stats.summary.open_rate}%)</span>
                    </div>
                    <div className="h-8 bg-green-500 rounded-lg" style={{ width: `${stats.summary.open_rate}%` }} />
                  </div>
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span>Clicked</span>
                      <span className="font-medium">{stats.summary.total_clicked} ({stats.summary.click_rate}%)</span>
                    </div>
                    <div className="h-8 bg-yellow-500 rounded-lg" style={{ width: `${stats.summary.click_rate}%` }} />
                  </div>
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span>Replied</span>
                      <span className="font-medium">{stats.summary.total_replied} ({stats.summary.reply_rate}%)</span>
                    </div>
                    <div className="h-8 bg-purple-500 rounded-lg" style={{ width: `${stats.summary.reply_rate}%` }} />
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Sequences Tab */}
        {activeTab === 'sequences' && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-semibold">Email Sequences</h3>
              <button
                onClick={() => setShowSequenceModal(true)}
                className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90"
              >
                <Plus className="w-4 h-4" />
                New Sequence
              </button>
            </div>

            {sequences.length === 0 ? (
              <div className="bg-white rounded-xl border border-border p-12 text-center">
                <ArrowRight className="w-12 h-12 mx-auto mb-4 text-slate-300" />
                <h3 className="font-semibold text-lg mb-2">No sequences yet</h3>
                <p className="text-secondary mb-4">
                  Create automated email sequences to nurture your leads
                </p>
                <button
                  onClick={() => setShowSequenceModal(true)}
                  className="px-4 py-2 bg-primary text-white rounded-lg"
                >
                  Create First Sequence
                </button>
              </div>
            ) : (
              <div className="grid gap-4">
                {sequences.map((sequence) => (
                  <motion.div
                    key={sequence.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-white rounded-xl border border-border p-5 hover:shadow-lg transition-shadow cursor-pointer"
                    onClick={() => setSelectedSequence(sequence)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                          sequence.status === 'active' ? 'bg-green-100' : 'bg-slate-100'
                        }`}>
                          {sequence.status === 'active' ? (
                            <Play className="w-6 h-6 text-green-600" />
                          ) : (
                            <Pause className="w-6 h-6 text-slate-600" />
                          )}
                        </div>
                        <div>
                          <h4 className="font-semibold text-foreground">{sequence.name}</h4>
                          <p className="text-sm text-secondary">
                            {sequence.steps?.length || 0} steps • {sequence.total_enrolled || 0} enrolled
                          </p>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-6">
                        <div className="text-center">
                          <p className="text-lg font-bold text-foreground">{sequence.total_enrolled || 0}</p>
                          <p className="text-xs text-secondary">Enrolled</p>
                        </div>
                        <div className="text-center">
                          <p className="text-lg font-bold text-green-600">{sequence.total_completed || 0}</p>
                          <p className="text-xs text-secondary">Completed</p>
                        </div>
                        <div className="text-center">
                          <p className="text-lg font-bold text-purple-600">{sequence.total_replied || 0}</p>
                          <p className="text-xs text-secondary">Replied</p>
                        </div>
                        <ChevronRight className="w-5 h-5 text-slate-400" />
                      </div>
                    </div>
                    
                    {/* Steps preview */}
                    {sequence.steps && sequence.steps.length > 0 && (
                      <div className="mt-4 flex items-center gap-2 overflow-x-auto pb-2">
                        {sequence.steps.map((step, i) => (
                          <div key={i} className="flex items-center gap-2">
                            <div className="px-3 py-1.5 bg-slate-100 rounded-lg text-xs whitespace-nowrap">
                              <span className="font-medium">Step {step.step_number}</span>
                              {step.delay_days > 0 && (
                                <span className="text-secondary ml-2">
                                  +{step.delay_days}d
                                </span>
                              )}
                            </div>
                            {i < sequence.steps.length - 1 && (
                              <ArrowRight className="w-4 h-4 text-slate-300" />
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </motion.div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Recent Emails Tab */}
        {activeTab === 'recent' && stats && (
          <div className="bg-white rounded-xl border border-border overflow-hidden">
            <div className="p-4 border-b border-border">
              <h3 className="font-semibold">Recent Tracked Emails</h3>
            </div>
            
            {stats.recent_emails?.length === 0 ? (
              <div className="p-12 text-center text-secondary">
                <Mail className="w-12 h-12 mx-auto mb-3 opacity-30" />
                <p>No tracked emails yet</p>
              </div>
            ) : (
              <div className="divide-y divide-border">
                {stats.recent_emails?.map((email) => (
                  <div key={email.id} className="p-4 hover:bg-slate-50 transition-colors">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                          email.status === 'replied' ? 'bg-purple-100' :
                          email.status === 'clicked' ? 'bg-yellow-100' :
                          email.status === 'opened' ? 'bg-green-100' : 'bg-blue-100'
                        }`}>
                          {email.status === 'replied' ? (
                            <MessageSquare className="w-5 h-5 text-purple-600" />
                          ) : email.status === 'clicked' ? (
                            <MousePointer className="w-5 h-5 text-yellow-600" />
                          ) : email.status === 'opened' ? (
                            <Eye className="w-5 h-5 text-green-600" />
                          ) : (
                            <Send className="w-5 h-5 text-blue-600" />
                          )}
                        </div>
                        <div>
                          <p className="font-medium text-foreground">{email.to_email}</p>
                          <p className="text-sm text-secondary line-clamp-1">{email.subject}</p>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-4">
                        <div className="text-right">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium capitalize ${
                            email.status === 'replied' ? 'bg-purple-100 text-purple-700' :
                            email.status === 'clicked' ? 'bg-yellow-100 text-yellow-700' :
                            email.status === 'opened' ? 'bg-green-100 text-green-700' :
                            'bg-blue-100 text-blue-700'
                          }`}>
                            {email.status}
                          </span>
                          <p className="text-xs text-secondary mt-1">
                            {email.open_count > 0 && `${email.open_count} opens`}
                            {email.click_count > 0 && ` • ${email.click_count} clicks`}
                          </p>
                        </div>
                        <div className="text-right text-sm text-secondary">
                          {format(new Date(email.sent_at), 'MMM d, h:mm a')}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </DashboardLayout>
  );
};

export default EmailAnalyticsPage;
