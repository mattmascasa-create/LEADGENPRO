import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Phone, Clock, TrendingUp, TrendingDown, BarChart3, PieChart,
  Play, Pause, Volume2, MessageSquare, AlertTriangle, CheckCircle,
  Target, Users, Lightbulb, Award, ChevronRight, Search, Filter,
  Mic, RefreshCw, Sparkles, ThumbsUp, ThumbsDown, Zap, FileText,
  Brain, Loader2, ChevronDown, ChevronUp, X
} from 'lucide-react';
import axios from 'axios';
import { toast } from 'react-toastify';
import { format } from 'date-fns';
import DashboardLayout from '@/components/DashboardLayout';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart as RechartsPieChart, Pie, Cell, LineChart, Line, Legend
} from 'recharts';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const COLORS = ['#10B981', '#F59E0B', '#EF4444', '#6366F1', '#8B5CF6'];

const CallAnalyticsDashboard = () => {
  const [analytics, setAnalytics] = useState(null);
  const [callLogs, setCallLogs] = useState([]);
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedCall, setSelectedCall] = useState(null);
  const [expandedCall, setExpandedCall] = useState(null);
  const [transcribing, setTranscribing] = useState({});
  const [analyzing, setAnalyzing] = useState({});
  const [timeRange, setTimeRange] = useState(30);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    fetchAllData();
  }, [timeRange]);

  const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return { Authorization: `Bearer ${token}` };
  };

  const fetchAllData = async () => {
    setLoading(true);
    try {
      const headers = getAuthHeaders();

      const [analyticsRes, logsRes, statsRes, leaderboardRes] = await Promise.all([
        axios.get(`${API_URL}/api/call-analytics?days=${timeRange}`, { headers }).catch(() => null),
        axios.get(`${API_URL}/api/calls/logs?limit=50`, { headers }).catch(() => ({ data: [] })),
        axios.get(`${API_URL}/api/calls/stats`, { headers }).catch(() => ({ data: null })),
        axios.get(`${API_URL}/api/call-analytics/leaderboard?days=${timeRange}`, { headers }).catch(() => ({ data: [] }))
      ]);

      // Merge analytics with stats
      const stats = statsRes?.data;
      const analyticsData = analyticsRes?.data || {};
      
      setAnalytics({
        overview: {
          total_calls: stats?.total_calls || analyticsData.overview?.total_calls || 0,
          total_duration_minutes: Math.round((stats?.total_duration_seconds || 0) / 60) || analyticsData.overview?.total_duration_minutes || 0,
          avg_duration_minutes: Math.round((stats?.average_duration_seconds || 0) / 60) || analyticsData.overview?.avg_duration_minutes || 0,
          avg_talk_ratio: analyticsData.overview?.avg_talk_ratio || 55,
          connect_rate: stats?.connect_rate || 0
        },
        sentiment: analyticsData.sentiment || { positive: 0, neutral: 0, negative: 0 },
        top_topics: analyticsData.top_topics || [],
        deal_signals: analyticsData.deal_signals || { buying_signals: 0, objections: 0, recent_signals: [] },
        coaching: analyticsData.coaching || { tips: [] },
        outcomes: stats?.outcomes || {}
      });

      setCallLogs(logsRes?.data || []);
      setLeaderboard(leaderboardRes?.data || []);
    } catch (error) {
      console.error('Failed to fetch analytics:', error);
      toast.error('Failed to load call analytics');
    } finally {
      setLoading(false);
    }
  };

  const [coaching, setCoaching] = useState({});
  const [teamInsights, setTeamInsights] = useState(null);
  const [loadingCoaching, setLoadingCoaching] = useState({});

  const transcribeCall = async (callId) => {
    setTranscribing(prev => ({ ...prev, [callId]: true }));
    try {
      const response = await axios.post(
        `${API_URL}/api/calls/${callId}/transcribe`,
        {},
        { headers: getAuthHeaders() }
      );
      
      if (response.data.success) {
        toast.success(response.data.already_transcribed ? 'Transcript loaded' : 'Call transcribed successfully!');
        setCallLogs(prev => prev.map(call => 
          call.id === callId 
            ? { ...call, transcript: response.data.transcript }
            : call
        ));
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to transcribe call');
    } finally {
      setTranscribing(prev => ({ ...prev, [callId]: false }));
    }
  };

  const analyzeCall = async (callId) => {
    setAnalyzing(prev => ({ ...prev, [callId]: true }));
    try {
      const response = await axios.post(
        `${API_URL}/api/calls/${callId}/analyze`,
        {},
        { headers: getAuthHeaders() }
      );
      
      if (response.data.success) {
        toast.success('AI analysis complete!');
        setCallLogs(prev => prev.map(call => 
          call.id === callId 
            ? { ...call, analysis: response.data.analysis }
            : call
        ));
        // Update the selected call modal if open
        if (selectedCall?.id === callId) {
          setSelectedCall({ ...selectedCall, analysis: response.data.analysis });
        }
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to analyze call');
    } finally {
      setAnalyzing(prev => ({ ...prev, [callId]: false }));
    }
  };

  // Get AI Coaching for a specific call
  const getCallCoaching = async (callId) => {
    setLoadingCoaching(prev => ({ ...prev, [callId]: true }));
    try {
      const response = await axios.post(
        `${API_URL}/api/calls/${callId}/coaching`,
        {},
        { headers: getAuthHeaders() }
      );
      
      if (response.data.success) {
        toast.success('AI Coaching generated!');
        setCoaching(prev => ({ ...prev, [callId]: response.data.coaching }));
        setCallLogs(prev => prev.map(call => 
          call.id === callId 
            ? { ...call, coaching: response.data.coaching }
            : call
        ));
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to get coaching. Make sure the call is transcribed first.');
    } finally {
      setLoadingCoaching(prev => ({ ...prev, [callId]: false }));
    }
  };

  // Fetch team coaching insights
  const fetchTeamInsights = async () => {
    try {
      const response = await axios.get(
        `${API_URL}/api/calls/coaching/team-insights?days=${timeRange}`,
        { headers: getAuthHeaders() }
      );
      setTeamInsights(response.data);
    } catch (error) {
      console.error('Failed to fetch team insights');
    }
  };

  useEffect(() => {
    if (activeTab === 'coaching') {
      fetchTeamInsights();
    }
  }, [activeTab, timeRange]);

  const formatDuration = (seconds) => {
    if (!seconds) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const sentimentData = analytics ? [
    { name: 'Positive', value: analytics.sentiment.positive || 0, color: '#10B981' },
    { name: 'Neutral', value: analytics.sentiment.neutral || 0, color: '#F59E0B' },
    { name: 'Negative', value: analytics.sentiment.negative || 0, color: '#EF4444' }
  ] : [];

  const outcomesData = analytics?.outcomes ? Object.entries(analytics.outcomes).map(([name, value]) => ({
    name: name.replace('_', ' '),
    value,
    color: name === 'connected' ? '#10B981' : 
           name === 'voicemail' ? '#3B82F6' : 
           name === 'no_answer' ? '#F59E0B' : '#6B7280'
  })) : [];

  const topicsData = analytics?.top_topics || [];

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
              <Sparkles className="w-8 h-8 text-primary" />
              Call Intelligence
            </h1>
            <p className="text-sm lg:text-base text-secondary">
              Gong-style analytics for your sales calls with AI-powered insights
            </p>
          </div>
          
          <div className="flex items-center gap-3">
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(parseInt(e.target.value))}
              className="px-4 py-2 border border-border rounded-lg bg-white text-sm"
            >
              <option value={7}>Last 7 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
            </select>
            <button
              onClick={fetchAllData}
              className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
            >
              <RefreshCw className="w-5 h-5 text-secondary" />
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {[
            { id: 'overview', label: 'Overview', icon: BarChart3 },
            { id: 'calls', label: 'Call History', icon: Phone },
            { id: 'coaching', label: 'AI Coaching', icon: Lightbulb },
            { id: 'leaderboard', label: 'Leaderboard', icon: Award }
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

        {/* Overview Tab */}
        {activeTab === 'overview' && analytics && (
          <div className="space-y-6">
            {/* Stats Grid */}
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-white p-5 rounded-xl border border-border"
              >
                <div className="flex items-center gap-3 mb-2">
                  <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                    <Phone className="w-5 h-5 text-blue-600" />
                  </div>
                </div>
                <p className="text-2xl font-bold text-foreground">{analytics.overview.total_calls}</p>
                <p className="text-sm text-secondary">Total Calls</p>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="bg-white p-5 rounded-xl border border-border"
              >
                <div className="flex items-center gap-3 mb-2">
                  <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                    <TrendingUp className="w-5 h-5 text-green-600" />
                  </div>
                </div>
                <p className="text-2xl font-bold text-foreground">{analytics.overview.connect_rate}%</p>
                <p className="text-sm text-secondary">Connect Rate</p>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="bg-white p-5 rounded-xl border border-border"
              >
                <div className="flex items-center gap-3 mb-2">
                  <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                    <Clock className="w-5 h-5 text-purple-600" />
                  </div>
                </div>
                <p className="text-2xl font-bold text-foreground">{analytics.overview.total_duration_minutes}m</p>
                <p className="text-sm text-secondary">Total Talk Time</p>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="bg-white p-5 rounded-xl border border-border"
              >
                <div className="flex items-center gap-3 mb-2">
                  <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
                    <Mic className="w-5 h-5 text-orange-600" />
                  </div>
                </div>
                <p className="text-2xl font-bold text-foreground">{analytics.overview.avg_duration_minutes}m</p>
                <p className="text-sm text-secondary">Avg Duration</p>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
                className="bg-white p-5 rounded-xl border border-border"
              >
                <div className="flex items-center gap-3 mb-2">
                  <div className="w-10 h-10 bg-indigo-100 rounded-lg flex items-center justify-center">
                    <MessageSquare className="w-5 h-5 text-indigo-600" />
                  </div>
                </div>
                <p className="text-2xl font-bold text-foreground">{analytics.overview.avg_talk_ratio}%</p>
                <p className="text-sm text-secondary">Talk Ratio</p>
              </motion.div>
            </div>

            {/* Charts Row */}
            <div className="grid lg:grid-cols-2 gap-6">
              {/* Outcomes Chart */}
              <div className="bg-white p-6 rounded-xl border border-border">
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <PieChart className="w-5 h-5 text-primary" />
                  Call Outcomes
                </h3>
                {outcomesData.length > 0 ? (
                  <>
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <RechartsPieChart>
                          <Pie
                            data={outcomesData}
                            cx="50%"
                            cy="50%"
                            innerRadius={60}
                            outerRadius={80}
                            paddingAngle={5}
                            dataKey="value"
                          >
                            {outcomesData.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={entry.color} />
                            ))}
                          </Pie>
                          <Tooltip />
                        </RechartsPieChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="flex flex-wrap justify-center gap-4 mt-4">
                      {outcomesData.map((item, idx) => (
                        <div key={idx} className="flex items-center gap-2">
                          <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
                          <span className="text-sm capitalize">{item.name}: {item.value}</span>
                        </div>
                      ))}
                    </div>
                  </>
                ) : (
                  <div className="h-64 flex items-center justify-center text-secondary">
                    <p>No call data yet</p>
                  </div>
                )}
              </div>

              {/* Sentiment Chart */}
              <div className="bg-white p-6 rounded-xl border border-border">
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <Brain className="w-5 h-5 text-primary" />
                  Call Sentiment (AI Analyzed)
                </h3>
                {sentimentData.some(d => d.value > 0) ? (
                  <>
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <RechartsPieChart>
                          <Pie
                            data={sentimentData}
                            cx="50%"
                            cy="50%"
                            innerRadius={60}
                            outerRadius={80}
                            paddingAngle={5}
                            dataKey="value"
                          >
                            {sentimentData.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={entry.color} />
                            ))}
                          </Pie>
                          <Tooltip />
                          <Legend />
                        </RechartsPieChart>
                      </ResponsiveContainer>
                    </div>
                  </>
                ) : (
                  <div className="h-64 flex flex-col items-center justify-center text-secondary">
                    <Brain className="w-12 h-12 mb-3 opacity-30" />
                    <p>Analyze calls to see sentiment data</p>
                    <p className="text-sm">Click "AI Analysis" on any call</p>
                  </div>
                )}
              </div>
            </div>

            {/* Topics & Deal Signals */}
            <div className="grid lg:grid-cols-2 gap-6">
              {/* Top Topics */}
              {topicsData.length > 0 && (
                <div className="bg-white p-6 rounded-xl border border-border">
                  <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <BarChart3 className="w-5 h-5 text-primary" />
                    Top Topics Discussed
                  </h3>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={topicsData} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis type="number" />
                        <YAxis dataKey="topic" type="category" width={100} />
                        <Tooltip />
                        <Bar dataKey="count" fill="#3B82F6" radius={[0, 4, 4, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {/* Deal Signals */}
              <div className="bg-white p-6 rounded-xl border border-border">
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <Zap className="w-5 h-5 text-yellow-500" />
                  Deal Signals Detected
                </h3>
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div className="bg-green-50 p-4 rounded-xl text-center">
                    <ThumbsUp className="w-6 h-6 text-green-600 mx-auto mb-2" />
                    <p className="text-2xl font-bold text-green-700">{analytics.deal_signals.buying_signals}</p>
                    <p className="text-sm text-green-600">Buying Signals</p>
                  </div>
                  <div className="bg-red-50 p-4 rounded-xl text-center">
                    <ThumbsDown className="w-6 h-6 text-red-600 mx-auto mb-2" />
                    <p className="text-2xl font-bold text-red-700">{analytics.deal_signals.objections}</p>
                    <p className="text-sm text-red-600">Objections</p>
                  </div>
                </div>
                {analytics.deal_signals.recent_signals?.length > 0 && (
                  <div className="space-y-2">
                    {analytics.deal_signals.recent_signals.slice(0, 3).map((signal, i) => (
                      <div key={i} className={`p-3 rounded-lg text-sm ${
                        signal.type === 'buying_signal' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'
                      }`}>
                        {signal.text}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Calls Tab */}
        {activeTab === 'calls' && (
          <div className="bg-white rounded-xl border border-border overflow-hidden">
            <div className="p-4 border-b border-border flex items-center justify-between">
              <div>
                <h3 className="font-semibold">Call History</h3>
                <p className="text-sm text-secondary">Click on a call to transcribe and analyze with AI</p>
              </div>
              <span className="text-sm text-secondary">{callLogs.length} calls</span>
            </div>
            
            {callLogs.length === 0 ? (
              <div className="p-12 text-center text-secondary">
                <Phone className="w-12 h-12 mx-auto mb-3 opacity-30" />
                <p className="font-medium">No calls recorded yet</p>
                <p className="text-sm">Make calls from the dialer to see them here</p>
              </div>
            ) : (
              <div className="divide-y divide-border">
                {callLogs.map((call) => (
                  <div key={call.id} className="hover:bg-slate-50 transition-colors">
                    <div
                      className="p-4 cursor-pointer flex items-center justify-between"
                      onClick={() => setExpandedCall(expandedCall === call.id ? null : call.id)}
                    >
                      <div className="flex items-center gap-4">
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                          call.outcome === 'connected' ? 'bg-green-100' :
                          call.outcome === 'voicemail' ? 'bg-blue-100' :
                          call.outcome === 'no_answer' ? 'bg-yellow-100' : 'bg-slate-100'
                        }`}>
                          <Phone className={`w-5 h-5 ${
                            call.outcome === 'connected' ? 'text-green-600' :
                            call.outcome === 'voicemail' ? 'text-blue-600' :
                            call.outcome === 'no_answer' ? 'text-yellow-600' : 'text-slate-600'
                          }`} />
                        </div>
                        <div>
                          <p className="font-medium text-foreground">{call.phone_number}</p>
                          <p className="text-sm text-secondary">
                            {format(new Date(call.created_at), 'MMM d, yyyy h:mm a')}
                          </p>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-3">
                        {call.transcript && (
                          <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded text-xs font-medium flex items-center gap-1">
                            <FileText className="w-3 h-3" /> Transcribed
                          </span>
                        )}
                        {call.analysis && (
                          <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs font-medium flex items-center gap-1">
                            <Brain className="w-3 h-3" /> Analyzed
                          </span>
                        )}
                        <span className={`px-3 py-1 rounded-full text-xs font-medium capitalize ${
                          call.outcome === 'connected' ? 'bg-green-100 text-green-700' :
                          call.outcome === 'voicemail' ? 'bg-blue-100 text-blue-700' :
                          call.outcome === 'no_answer' ? 'bg-yellow-100 text-yellow-700' :
                          'bg-slate-100 text-slate-700'
                        }`}>
                          {call.outcome?.replace('_', ' ') || 'Unknown'}
                        </span>
                        <span className="text-sm text-secondary w-12 text-right">
                          {formatDuration(call.duration)}
                        </span>
                        {expandedCall === call.id ? (
                          <ChevronUp className="w-5 h-5 text-secondary" />
                        ) : (
                          <ChevronDown className="w-5 h-5 text-secondary" />
                        )}
                      </div>
                    </div>
                    
                    {/* Expanded Call Details */}
                    {expandedCall === call.id && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="px-4 pb-4 space-y-4"
                      >
                        {/* Action Buttons */}
                        <div className="flex flex-wrap gap-3 pt-2 border-t border-border">
                          {call.recording_url && !call.transcript && (
                            <button
                              onClick={(e) => { e.stopPropagation(); transcribeCall(call.id); }}
                              disabled={transcribing[call.id]}
                              className="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 disabled:opacity-50 flex items-center gap-2"
                            >
                              {transcribing[call.id] ? (
                                <><Loader2 className="w-4 h-4 animate-spin" /> Transcribing...</>
                              ) : (
                                <><FileText className="w-4 h-4" /> Transcribe with Whisper</>
                              )}
                            </button>
                          )}
                          <button
                            onClick={(e) => { e.stopPropagation(); analyzeCall(call.id); }}
                            disabled={analyzing[call.id]}
                            className="px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2"
                          >
                            {analyzing[call.id] ? (
                              <><Loader2 className="w-4 h-4 animate-spin" /> Analyzing...</>
                            ) : (
                              <><Brain className="w-4 h-4" /> {call.analysis ? 'Re-analyze with AI' : 'Analyze with AI'}</>
                            )}
                          </button>
                          <button
                            onClick={(e) => { e.stopPropagation(); setSelectedCall(call); }}
                            className="px-4 py-2 border border-border rounded-lg text-sm font-medium hover:bg-slate-50 flex items-center gap-2"
                          >
                            <ChevronRight className="w-4 h-4" /> View Full Details
                          </button>
                        </div>

                        {/* Recording Player */}
                        {call.recording_url && (
                          <div className="p-4 bg-slate-50 rounded-lg">
                            <p className="text-sm font-medium mb-2 flex items-center gap-2">
                              <Mic className="w-4 h-4" /> Call Recording
                            </p>
                            <audio controls className="w-full" src={call.recording_url}>
                              Your browser does not support audio.
                            </audio>
                          </div>
                        )}

                        {/* Quick Transcript Preview */}
                        {call.transcript && (
                          <div className="p-4 bg-slate-50 rounded-lg">
                            <p className="text-sm font-medium mb-2 flex items-center gap-2">
                              <MessageSquare className="w-4 h-4" /> Transcript Preview
                            </p>
                            <p className="text-sm text-secondary line-clamp-3">
                              {call.transcript}
                            </p>
                          </div>
                        )}

                        {/* Quick Analysis Summary */}
                        {call.analysis && (
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                            <div className="p-3 bg-slate-50 rounded-lg text-center">
                              <p className="text-xs text-secondary mb-1">Sentiment</p>
                              <p className={`font-bold ${
                                call.analysis.sentiment?.overall >= 0.6 ? 'text-green-600' :
                                call.analysis.sentiment?.overall < 0.4 ? 'text-red-600' : 'text-yellow-600'
                              }`}>
                                {call.analysis.sentiment?.overall >= 0.6 ? 'Positive' :
                                 call.analysis.sentiment?.overall < 0.4 ? 'Negative' : 'Neutral'}
                              </p>
                            </div>
                            <div className="p-3 bg-slate-50 rounded-lg text-center">
                              <p className="text-xs text-secondary mb-1">Talk Ratio</p>
                              <p className="font-bold">{call.analysis.talk_ratio?.rep_percentage || 50}%</p>
                            </div>
                            <div className="p-3 bg-slate-50 rounded-lg text-center">
                              <p className="text-xs text-secondary mb-1">Questions</p>
                              <p className="font-bold">{call.analysis.questions?.total_asked || 0}</p>
                            </div>
                            <div className="p-3 bg-slate-50 rounded-lg text-center">
                              <p className="text-xs text-secondary mb-1">Score</p>
                              <p className={`font-bold ${
                                call.analysis.overall_score >= 80 ? 'text-green-600' :
                                call.analysis.overall_score >= 60 ? 'text-yellow-600' : 'text-red-600'
                              }`}>
                                {call.analysis.overall_score || '--'}
                              </p>
                            </div>
                          </div>
                        )}

                        {!call.recording_url && (
                          <div className="p-4 bg-slate-50 rounded-lg text-center text-secondary">
                            <Mic className="w-8 h-8 mx-auto mb-2 opacity-30" />
                            <p className="text-sm">No recording available</p>
                            <p className="text-xs">Enable call recording to get AI transcription and analysis</p>
                          </div>
                        )}
                      </motion.div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Coaching Tab */}
        {activeTab === 'coaching' && analytics && (
          <div className="space-y-6">
            {/* Team Insights Summary */}
            {teamInsights && (
              <div className="bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl p-6 text-white">
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <Users className="w-5 h-5" />
                  Team Performance Insights
                </h3>
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="bg-white/10 rounded-lg p-4">
                    <p className="text-3xl font-bold">{Math.round(teamInsights.team_avg_score)}</p>
                    <p className="text-sm opacity-80">Team Avg Score</p>
                  </div>
                  <div className="bg-white/10 rounded-lg p-4">
                    <p className="text-3xl font-bold">{teamInsights.total_calls_analyzed || 0}</p>
                    <p className="text-sm opacity-80">Calls Analyzed</p>
                  </div>
                  <div className="bg-white/10 rounded-lg p-4">
                    <p className="text-3xl font-bold">{teamInsights.score_distribution?.excellent || 0}</p>
                    <p className="text-sm opacity-80">Excellent Calls (80+)</p>
                  </div>
                  <div className="bg-white/10 rounded-lg p-4">
                    <p className="text-3xl font-bold">{teamInsights.score_distribution?.needs_work || 0}</p>
                    <p className="text-sm opacity-80">Need Improvement</p>
                  </div>
                </div>
                
                {/* Top Performers */}
                {teamInsights.top_performers?.length > 0 && (
                  <div className="mt-4">
                    <p className="text-sm font-medium mb-2">Top Performers:</p>
                    <div className="flex flex-wrap gap-2">
                      {teamInsights.top_performers.slice(0, 3).map((perf, i) => (
                        <span key={i} className="bg-white/20 px-3 py-1 rounded-full text-sm">
                          {i === 0 ? '🥇' : i === 1 ? '🥈' : '🥉'} {perf.name} ({Math.round(perf.avg_score)})
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Get AI Coaching for Calls */}
            <div className="bg-white rounded-xl border border-border p-6">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Brain className="w-5 h-5 text-purple-500" />
                Get Deep AI Coaching
              </h3>
              <p className="text-secondary mb-4">
                Select a transcribed call to receive comprehensive AI coaching with real-time suggestions, sentiment analysis, and personalized improvement tips.
              </p>
              
              <div className="space-y-3 max-h-64 overflow-y-auto">
                {callLogs.filter(call => call.transcript).map(call => (
                  <div key={call.id} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                        <Phone className="w-5 h-5 text-green-600" />
                      </div>
                      <div>
                        <p className="font-medium">{call.phone_number}</p>
                        <p className="text-sm text-secondary">
                          {format(new Date(call.created_at), 'MMM d, yyyy h:mm a')} • {formatDuration(call.duration)}
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={() => getCallCoaching(call.id)}
                      disabled={loadingCoaching[call.id]}
                      className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 flex items-center gap-2"
                    >
                      {loadingCoaching[call.id] ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Analyzing...
                        </>
                      ) : coaching[call.id] ? (
                        <>
                          <CheckCircle className="w-4 h-4" />
                          View Coaching
                        </>
                      ) : (
                        <>
                          <Sparkles className="w-4 h-4" />
                          Get Coaching
                        </>
                      )}
                    </button>
                  </div>
                ))}
                
                {callLogs.filter(call => call.transcript).length === 0 && (
                  <div className="text-center py-8 text-secondary">
                    <Mic className="w-12 h-12 mx-auto mb-3 opacity-30" />
                    <p>No transcribed calls available</p>
                    <p className="text-sm">Transcribe a call first to get AI coaching</p>
                  </div>
                )}
              </div>
            </div>

            {/* Display Coaching Results */}
            {Object.entries(coaching).map(([callId, coachingData]) => (
              <motion.div
                key={callId}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-white rounded-xl border border-border overflow-hidden"
              >
                <div className="p-4 bg-gradient-to-r from-purple-50 to-indigo-50 border-b border-border">
                  <h4 className="font-semibold flex items-center gap-2">
                    <Target className="w-5 h-5 text-purple-600" />
                    AI Coaching Results
                    <span className="ml-auto px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-sm font-bold">
                      Score: {coachingData.overall_score || 'N/A'}/100
                    </span>
                  </h4>
                </div>
                
                <div className="p-6 space-y-6">
                  {/* Real-time Suggestions */}
                  {coachingData.real_time_suggestions?.length > 0 && (
                    <div>
                      <h5 className="font-medium mb-3 flex items-center gap-2">
                        <Zap className="w-4 h-4 text-yellow-500" />
                        Real-time Coaching Moments
                      </h5>
                      <div className="space-y-2">
                        {coachingData.real_time_suggestions.slice(0, 5).map((suggestion, i) => (
                          <div key={i} className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                            <p className="text-sm font-medium text-yellow-800">{suggestion.moment}</p>
                            <p className="text-sm text-yellow-700 mt-1">{suggestion.suggestion}</p>
                            <span className="inline-block mt-2 px-2 py-0.5 bg-yellow-200 text-yellow-800 text-xs rounded">
                              {suggestion.skill}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Talk to Listen Analysis */}
                  {coachingData.talk_to_listen_analysis && (
                    <div>
                      <h5 className="font-medium mb-3 flex items-center gap-2">
                        <MessageSquare className="w-4 h-4 text-blue-500" />
                        Talk-to-Listen Ratio
                      </h5>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="p-4 bg-blue-50 rounded-lg">
                          <p className="text-3xl font-bold text-blue-700">
                            {coachingData.talk_to_listen_analysis.rep_talk_percentage || 0}%
                          </p>
                          <p className="text-sm text-blue-600">Your Talk Time</p>
                        </div>
                        <div className="p-4 bg-green-50 rounded-lg">
                          <p className="text-3xl font-bold text-green-700">
                            {coachingData.talk_to_listen_analysis.customer_talk_percentage || 0}%
                          </p>
                          <p className="text-sm text-green-600">Customer Talk Time</p>
                        </div>
                      </div>
                      <p className="mt-3 text-sm text-secondary">
                        {coachingData.talk_to_listen_analysis.recommendation}
                      </p>
                    </div>
                  )}

                  {/* Sentiment Analysis */}
                  {coachingData.sentiment_analysis && (
                    <div>
                      <h5 className="font-medium mb-3 flex items-center gap-2">
                        {coachingData.sentiment_analysis.overall_sentiment === 'positive' 
                          ? <ThumbsUp className="w-4 h-4 text-green-500" />
                          : coachingData.sentiment_analysis.overall_sentiment === 'negative'
                            ? <ThumbsDown className="w-4 h-4 text-red-500" />
                            : <Target className="w-4 h-4 text-yellow-500" />
                        }
                        Sentiment Analysis
                      </h5>
                      <div className={`p-4 rounded-lg ${
                        coachingData.sentiment_analysis.overall_sentiment === 'positive' 
                          ? 'bg-green-50' 
                          : coachingData.sentiment_analysis.overall_sentiment === 'negative'
                            ? 'bg-red-50'
                            : 'bg-yellow-50'
                      }`}>
                        <p className="font-medium capitalize">
                          Overall: {coachingData.sentiment_analysis.overall_sentiment}
                        </p>
                        {coachingData.sentiment_analysis.alerts?.length > 0 && (
                          <div className="mt-2">
                            <p className="text-sm font-medium text-red-600">Alerts:</p>
                            <ul className="text-sm text-red-700">
                              {coachingData.sentiment_analysis.alerts.map((alert, i) => (
                                <li key={i}>• {alert}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Coaching Recommendations */}
                  {coachingData.coaching_recommendations && (
                    <div>
                      <h5 className="font-medium mb-3 flex items-center gap-2">
                        <Lightbulb className="w-4 h-4 text-yellow-500" />
                        Personalized Recommendations
                      </h5>
                      <div className="space-y-3">
                        <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                          <p className="text-sm font-medium text-green-800">Top Strength</p>
                          <p className="text-green-700">{coachingData.coaching_recommendations.top_strength}</p>
                        </div>
                        <div className="p-4 bg-orange-50 border border-orange-200 rounded-lg">
                          <p className="text-sm font-medium text-orange-800">Priority Improvement</p>
                          <p className="text-orange-700">{coachingData.coaching_recommendations.priority_improvement}</p>
                        </div>
                        {coachingData.coaching_recommendations.specific_tips?.length > 0 && (
                          <div className="space-y-2">
                            {coachingData.coaching_recommendations.specific_tips.map((tip, i) => (
                              <div key={i} className="p-3 bg-slate-50 rounded-lg">
                                <p className="text-sm font-medium">{tip.skill}: {tip.tip}</p>
                                {tip.example && (
                                  <p className="text-sm text-secondary mt-1 italic">Example: "{tip.example}"</p>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </motion.div>
            ))}

            <div className="bg-white rounded-xl border border-border p-6">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Lightbulb className="w-5 h-5 text-yellow-500" />
                AI Coaching Insights
              </h3>
              <p className="text-secondary mb-6">
                Based on analysis of your recent calls, here are personalized improvement suggestions:
              </p>
              
              {analytics.coaching.tips?.length > 0 ? (
                <div className="space-y-4">
                  {analytics.coaching.tips.map((item, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.1 }}
                      className="flex items-start gap-4 p-4 bg-yellow-50 border border-yellow-200 rounded-xl"
                    >
                      <div className="w-8 h-8 bg-yellow-200 rounded-full flex items-center justify-center flex-shrink-0">
                        <span className="text-yellow-800 font-bold">{i + 1}</span>
                      </div>
                      <div className="flex-1">
                        <p className="font-medium text-yellow-900">{item.tip}</p>
                        <p className="text-sm text-yellow-700 mt-1">
                          Found in {item.occurrences} calls
                        </p>
                      </div>
                      <ChevronRight className="w-5 h-5 text-yellow-600" />
                    </motion.div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-secondary">
                  <Brain className="w-12 h-12 mx-auto mb-3 opacity-30" />
                  <p>Analyze more calls to get personalized coaching tips</p>
                </div>
              )}
            </div>

            {/* Talk Ratio Guidance */}
            <div className="bg-white rounded-xl border border-border p-6">
              <h3 className="text-lg font-semibold mb-4">Talk Ratio Analysis</h3>
              <div className="flex items-center gap-6">
                <div className="relative w-32 h-32 flex-shrink-0">
                  <svg className="w-full h-full transform -rotate-90">
                    <circle
                      cx="64"
                      cy="64"
                      r="56"
                      stroke="#E5E7EB"
                      strokeWidth="12"
                      fill="none"
                    />
                    <circle
                      cx="64"
                      cy="64"
                      r="56"
                      stroke={analytics.overview.avg_talk_ratio > 60 ? '#F59E0B' : '#10B981'}
                      strokeWidth="12"
                      fill="none"
                      strokeDasharray={`${analytics.overview.avg_talk_ratio * 3.51} 351`}
                    />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-2xl font-bold">{analytics.overview.avg_talk_ratio}%</span>
                  </div>
                </div>
                <div>
                  <p className="text-lg font-medium text-foreground mb-2">Your Average Talk Time</p>
                  <p className="text-secondary">
                    {analytics.overview.avg_talk_ratio > 60 
                      ? 'You tend to talk more than your prospects. Try asking more open-ended questions and practice active listening.'
                      : analytics.overview.avg_talk_ratio < 40
                        ? 'You\'re a great listener! Make sure you\'re also providing enough value and guidance during calls.'
                        : 'Great balance! You\'re maintaining healthy conversation dynamics.'
                    }
                  </p>
                  <div className="mt-4 flex items-center gap-4 text-sm">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 bg-green-500 rounded-full" />
                      <span>Ideal: 40-60%</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className={`w-3 h-3 rounded-full ${
                        analytics.overview.avg_talk_ratio > 60 ? 'bg-yellow-500' : 'bg-green-500'
                      }`} />
                      <span>Your avg: {analytics.overview.avg_talk_ratio}%</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Best Practices */}
            <div className="bg-gradient-to-r from-primary/10 to-accent/10 rounded-xl border border-primary/20 p-6">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Award className="w-5 h-5 text-primary" />
                Sales Call Best Practices
              </h3>
              <div className="grid md:grid-cols-2 gap-4">
                <div className="bg-white p-4 rounded-lg">
                  <h4 className="font-medium text-green-700 mb-2 flex items-center gap-2">
                    <CheckCircle className="w-4 h-4" /> Do
                  </h4>
                  <ul className="text-sm space-y-2 text-secondary">
                    <li>• Use open-ended discovery questions</li>
                    <li>• Listen actively and take notes</li>
                    <li>• Set clear next steps at end of call</li>
                    <li>• Reference previous conversations</li>
                  </ul>
                </div>
                <div className="bg-white p-4 rounded-lg">
                  <h4 className="font-medium text-red-700 mb-2 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4" /> Avoid
                  </h4>
                  <ul className="text-sm space-y-2 text-secondary">
                    <li>• Talking more than 60% of the time</li>
                    <li>• Jumping straight to pitching</li>
                    <li>• Ignoring customer objections</li>
                    <li>• Ending without a clear CTA</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Leaderboard Tab */}
        {activeTab === 'leaderboard' && (
          <div className="bg-white rounded-xl border border-border overflow-hidden">
            <div className="p-4 border-b border-border">
              <h3 className="font-semibold flex items-center gap-2">
                <Award className="w-5 h-5 text-yellow-500" />
                Team Call Performance
              </h3>
            </div>
            
            {leaderboard.length === 0 ? (
              <div className="p-12 text-center text-secondary">
                <Users className="w-12 h-12 mx-auto mb-3 opacity-30" />
                <p className="font-medium">No team data available yet</p>
                <p className="text-sm">Team members need to make calls to appear here</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="text-left px-4 py-3 text-sm font-semibold text-secondary">Rank</th>
                      <th className="text-left px-4 py-3 text-sm font-semibold text-secondary">Rep</th>
                      <th className="text-left px-4 py-3 text-sm font-semibold text-secondary">Calls</th>
                      <th className="text-left px-4 py-3 text-sm font-semibold text-secondary">Duration</th>
                      <th className="text-left px-4 py-3 text-sm font-semibold text-secondary">Connect Rate</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {leaderboard.map((rep, i) => (
                      <tr key={rep.user_id} className="hover:bg-slate-50">
                        <td className="px-4 py-3">
                          <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold ${
                            i === 0 ? 'bg-yellow-100 text-yellow-700' :
                            i === 1 ? 'bg-slate-200 text-slate-700' :
                            i === 2 ? 'bg-orange-100 text-orange-700' :
                            'bg-slate-100 text-slate-600'
                          }`}>
                            {i + 1}
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <p className="font-medium text-foreground">{rep.name}</p>
                          <p className="text-xs text-secondary">{rep.email}</p>
                        </td>
                        <td className="px-4 py-3 font-medium">{rep.total_calls}</td>
                        <td className="px-4 py-3">{rep.total_duration_minutes}m</td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                            rep.connect_rate >= 70 ? 'bg-green-100 text-green-700' :
                            rep.connect_rate >= 50 ? 'bg-yellow-100 text-yellow-700' :
                            'bg-red-100 text-red-700'
                          }`}>
                            {rep.connect_rate}%
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Call Detail Modal */}
        {selectedCall && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="bg-white rounded-2xl shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto"
            >
              <div className="p-6 border-b border-border flex items-center justify-between sticky top-0 bg-white z-10">
                <div>
                  <h3 className="text-lg font-semibold">Call Details</h3>
                  <p className="text-sm text-secondary">{selectedCall.phone_number}</p>
                </div>
                <button
                  onClick={() => setSelectedCall(null)}
                  className="p-2 hover:bg-slate-100 rounded-lg"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              
              <div className="p-6 space-y-6">
                {/* Call Info */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="text-center p-3 bg-slate-50 rounded-lg">
                    <p className="text-xs text-secondary">Date</p>
                    <p className="font-medium">{format(new Date(selectedCall.created_at), 'MMM d, yyyy')}</p>
                  </div>
                  <div className="text-center p-3 bg-slate-50 rounded-lg">
                    <p className="text-xs text-secondary">Duration</p>
                    <p className="font-medium">{formatDuration(selectedCall.duration)}</p>
                  </div>
                  <div className="text-center p-3 bg-slate-50 rounded-lg">
                    <p className="text-xs text-secondary">Outcome</p>
                    <p className="font-medium capitalize">{selectedCall.outcome?.replace('_', ' ')}</p>
                  </div>
                  <div className="text-center p-3 bg-slate-50 rounded-lg">
                    <p className="text-xs text-secondary">Status</p>
                    <p className="font-medium flex items-center justify-center gap-1">
                      {selectedCall.analysis ? (
                        <><CheckCircle className="w-4 h-4 text-green-500" /> Analyzed</>
                      ) : selectedCall.transcript ? (
                        <><FileText className="w-4 h-4 text-purple-500" /> Transcribed</>
                      ) : (
                        <><AlertTriangle className="w-4 h-4 text-yellow-500" /> Pending</>
                      )}
                    </p>
                  </div>
                </div>

                {/* Recording */}
                {selectedCall.recording_url && (
                  <div className="p-4 bg-slate-50 rounded-lg">
                    <p className="text-sm font-medium mb-2 flex items-center gap-2">
                      <Mic className="w-4 h-4" /> Recording
                    </p>
                    <audio controls className="w-full" src={selectedCall.recording_url} />
                  </div>
                )}

                {/* Transcript */}
                {selectedCall.transcript && (
                  <div>
                    <h4 className="font-medium mb-2 flex items-center gap-2">
                      <MessageSquare className="w-4 h-4" /> Full Transcript
                    </h4>
                    <div className="p-4 bg-slate-50 rounded-lg max-h-64 overflow-y-auto">
                      <p className="text-sm whitespace-pre-wrap">{selectedCall.transcript}</p>
                    </div>
                  </div>
                )}

                {/* Analysis */}
                {selectedCall.analysis && (
                  <div className="space-y-4">
                    <h4 className="font-medium flex items-center gap-2">
                      <Brain className="w-4 h-4" /> AI Analysis
                    </h4>
                    
                    {/* Score */}
                    {selectedCall.analysis.overall_score && (
                      <div className="flex items-center gap-4">
                        <div className={`w-16 h-16 rounded-full flex items-center justify-center text-xl font-bold ${
                          selectedCall.analysis.overall_score >= 80 ? 'bg-green-100 text-green-700' :
                          selectedCall.analysis.overall_score >= 60 ? 'bg-yellow-100 text-yellow-700' :
                          'bg-red-100 text-red-700'
                        }`}>
                          {selectedCall.analysis.overall_score}
                        </div>
                        <div>
                          <p className="font-medium">Overall Score</p>
                          <p className="text-sm text-secondary">{selectedCall.analysis.call_summary}</p>
                        </div>
                      </div>
                    )}

                    {/* Key Topics */}
                    {selectedCall.analysis.key_topics?.length > 0 && (
                      <div>
                        <p className="text-sm font-medium mb-2">Key Topics</p>
                        <div className="flex flex-wrap gap-2">
                          {selectedCall.analysis.key_topics.map((topic, i) => (
                            <span key={i} className="px-3 py-1 bg-primary/10 text-primary rounded-full text-sm">
                              {topic}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Coaching Tips */}
                    {selectedCall.analysis.coaching_insights?.improvements?.length > 0 && (
                      <div className="bg-yellow-50 p-4 rounded-lg">
                        <p className="text-sm font-medium text-yellow-800 mb-2">Areas to Improve</p>
                        <ul className="text-sm text-yellow-700 space-y-1">
                          {selectedCall.analysis.coaching_insights.improvements.map((tip, i) => (
                            <li key={i}>• {tip}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex gap-3 pt-4 border-t border-border">
                  {selectedCall.recording_url && !selectedCall.transcript && (
                    <button
                      onClick={() => transcribeCall(selectedCall.id)}
                      disabled={transcribing[selectedCall.id]}
                      className="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 disabled:opacity-50 flex items-center gap-2"
                    >
                      {transcribing[selectedCall.id] ? (
                        <><Loader2 className="w-4 h-4 animate-spin" /> Transcribing...</>
                      ) : (
                        <><FileText className="w-4 h-4" /> Transcribe</>
                      )}
                    </button>
                  )}
                  <button
                    onClick={() => analyzeCall(selectedCall.id)}
                    disabled={analyzing[selectedCall.id]}
                    className="px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2"
                  >
                    {analyzing[selectedCall.id] ? (
                      <><Loader2 className="w-4 h-4 animate-spin" /> Analyzing...</>
                    ) : (
                      <><Brain className="w-4 h-4" /> {selectedCall.analysis ? 'Re-analyze' : 'Analyze'}</>
                    )}
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
};

export default CallAnalyticsDashboard;
