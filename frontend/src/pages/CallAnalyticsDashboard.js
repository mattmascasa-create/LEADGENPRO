import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Phone, Clock, TrendingUp, TrendingDown, BarChart3, PieChart,
  Play, Pause, Volume2, MessageSquare, AlertTriangle, CheckCircle,
  Target, Users, Lightbulb, Award, ChevronRight, Search, Filter,
  Mic, RefreshCw, Sparkles, ThumbsUp, ThumbsDown, Zap
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
  const [recordings, setRecordings] = useState([]);
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedRecording, setSelectedRecording] = useState(null);
  const [analyzingCall, setAnalyzingCall] = useState(null);
  const [timeRange, setTimeRange] = useState(30);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    fetchAllData();
  }, [timeRange]);

  const fetchAllData = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };

      const [analyticsRes, recordingsRes, leaderboardRes] = await Promise.all([
        axios.get(`${API_URL}/api/call-analytics?days=${timeRange}`, { headers }),
        axios.get(`${API_URL}/api/call-recordings?limit=20`, { headers }),
        axios.get(`${API_URL}/api/call-analytics/leaderboard?days=${timeRange}`, { headers }).catch(() => ({ data: [] }))
      ]);

      setAnalytics(analyticsRes.data);
      setRecordings(recordingsRes.data);
      setLeaderboard(leaderboardRes.data);
    } catch (error) {
      console.error('Failed to fetch analytics:', error);
      // Set mock data for demo
      setAnalytics({
        overview: {
          total_calls: 156,
          total_duration_minutes: 487,
          avg_duration_minutes: 3.1,
          avg_talk_ratio: 62
        },
        sentiment: { positive: 89, neutral: 52, negative: 15 },
        top_topics: [
          { topic: 'Pricing', count: 45 },
          { topic: 'Features', count: 38 },
          { topic: 'Implementation', count: 32 },
          { topic: 'Support', count: 28 },
          { topic: 'Integration', count: 21 }
        ],
        deal_signals: {
          buying_signals: 34,
          objections: 18,
          recent_signals: []
        },
        coaching: {
          tips: [
            { tip: 'Ask more discovery questions', occurrences: 12 },
            { tip: 'Let the prospect talk more', occurrences: 8 },
            { tip: 'Address pricing concerns proactively', occurrences: 6 }
          ]
        },
        recent_calls: []
      });
    } finally {
      setLoading(false);
    }
  };

  const analyzeCall = async (callId) => {
    setAnalyzingCall(callId);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(
        `${API_URL}/api/call-recordings/${callId}/analyze`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Call analyzed successfully!');
      setSelectedRecording(response.data);
      fetchAllData();
    } catch (error) {
      toast.error('Failed to analyze call');
    } finally {
      setAnalyzingCall(null);
    }
  };

  const sentimentData = analytics ? [
    { name: 'Positive', value: analytics.sentiment.positive, color: '#10B981' },
    { name: 'Neutral', value: analytics.sentiment.neutral, color: '#F59E0B' },
    { name: 'Negative', value: analytics.sentiment.negative, color: '#EF4444' }
  ] : [];

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
              Gong-style analytics for your sales calls
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
            { id: 'recordings', label: 'Recordings', icon: Mic },
            { id: 'coaching', label: 'Coaching', icon: Lightbulb },
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
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-white p-6 rounded-xl border border-border"
              >
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                    <Phone className="w-5 h-5 text-blue-600" />
                  </div>
                  <span className="text-sm text-secondary">Total Calls</span>
                </div>
                <p className="text-3xl font-bold text-foreground">{analytics.overview.total_calls}</p>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="bg-white p-6 rounded-xl border border-border"
              >
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                    <Clock className="w-5 h-5 text-green-600" />
                  </div>
                  <span className="text-sm text-secondary">Total Time</span>
                </div>
                <p className="text-3xl font-bold text-foreground">{analytics.overview.total_duration_minutes}m</p>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="bg-white p-6 rounded-xl border border-border"
              >
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                    <TrendingUp className="w-5 h-5 text-purple-600" />
                  </div>
                  <span className="text-sm text-secondary">Avg Duration</span>
                </div>
                <p className="text-3xl font-bold text-foreground">{analytics.overview.avg_duration_minutes}m</p>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="bg-white p-6 rounded-xl border border-border"
              >
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
                    <MessageSquare className="w-5 h-5 text-orange-600" />
                  </div>
                  <span className="text-sm text-secondary">Talk Ratio</span>
                </div>
                <p className="text-3xl font-bold text-foreground">{analytics.overview.avg_talk_ratio}%</p>
                <p className="text-xs text-secondary mt-1">
                  {analytics.overview.avg_talk_ratio > 60 ? '⚠️ Talk less, listen more' : '✅ Good balance'}
                </p>
              </motion.div>
            </div>

            {/* Charts Row */}
            <div className="grid lg:grid-cols-2 gap-6">
              {/* Sentiment Chart */}
              <div className="bg-white p-6 rounded-xl border border-border">
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <PieChart className="w-5 h-5 text-primary" />
                  Call Sentiment
                </h3>
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
              </div>

              {/* Topics Chart */}
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
            </div>

            {/* Deal Signals */}
            <div className="grid lg:grid-cols-2 gap-6">
              <div className="bg-white p-6 rounded-xl border border-border">
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <ThumbsUp className="w-5 h-5 text-green-600" />
                  Buying Signals Detected
                </h3>
                <div className="text-4xl font-bold text-green-600 mb-2">
                  {analytics.deal_signals.buying_signals}
                </div>
                <p className="text-sm text-secondary">
                  Positive indicators found in conversations
                </p>
                <div className="mt-4 space-y-2">
                  {analytics.deal_signals.recent_signals
                    .filter(s => s.type === 'buying_signal')
                    .slice(0, 3)
                    .map((signal, i) => (
                      <div key={i} className="flex items-start gap-2 p-2 bg-green-50 rounded-lg text-sm">
                        <Zap className="w-4 h-4 text-green-600 mt-0.5" />
                        <span className="text-green-800">{signal.text}</span>
                      </div>
                    ))}
                </div>
              </div>

              <div className="bg-white p-6 rounded-xl border border-border">
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <ThumbsDown className="w-5 h-5 text-red-600" />
                  Objections Raised
                </h3>
                <div className="text-4xl font-bold text-red-600 mb-2">
                  {analytics.deal_signals.objections}
                </div>
                <p className="text-sm text-secondary">
                  Concerns or objections to address
                </p>
                <div className="mt-4 space-y-2">
                  {analytics.deal_signals.recent_signals
                    .filter(s => s.type === 'objection')
                    .slice(0, 3)
                    .map((signal, i) => (
                      <div key={i} className="flex items-start gap-2 p-2 bg-red-50 rounded-lg text-sm">
                        <AlertTriangle className="w-4 h-4 text-red-600 mt-0.5" />
                        <span className="text-red-800">{signal.text}</span>
                      </div>
                    ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Recordings Tab */}
        {activeTab === 'recordings' && (
          <div className="space-y-4">
            <div className="bg-white rounded-xl border border-border overflow-hidden">
              <div className="p-4 border-b border-border">
                <h3 className="font-semibold">Recent Call Recordings</h3>
              </div>
              
              {recordings.length === 0 ? (
                <div className="p-8 text-center text-secondary">
                  <Mic className="w-12 h-12 mx-auto mb-3 opacity-30" />
                  <p>No recordings yet. Call recordings will appear here after calls are made.</p>
                </div>
              ) : (
                <div className="divide-y divide-border">
                  {recordings.map((recording) => (
                    <div key={recording.id} className="p-4 hover:bg-slate-50 transition-colors">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                            recording.sentiment === 'positive' ? 'bg-green-100' :
                            recording.sentiment === 'negative' ? 'bg-red-100' : 'bg-yellow-100'
                          }`}>
                            <Phone className={`w-5 h-5 ${
                              recording.sentiment === 'positive' ? 'text-green-600' :
                              recording.sentiment === 'negative' ? 'text-red-600' : 'text-yellow-600'
                            }`} />
                          </div>
                          <div>
                            <p className="font-medium text-foreground">
                              Call #{recording.call_id?.slice(0, 8)}
                            </p>
                            <p className="text-sm text-secondary">
                              {format(new Date(recording.created_at), 'MMM d, yyyy h:mm a')}
                              <span className="mx-2">•</span>
                              {Math.round(recording.duration_seconds / 60)} min
                            </p>
                          </div>
                        </div>
                        
                        <div className="flex items-center gap-2">
                          {recording.sentiment && (
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                              recording.sentiment === 'positive' ? 'bg-green-100 text-green-700' :
                              recording.sentiment === 'negative' ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'
                            }`}>
                              {recording.sentiment}
                            </span>
                          )}
                          <button
                            onClick={() => setSelectedRecording(recording)}
                            className="px-3 py-1.5 bg-primary text-white rounded-lg text-sm hover:bg-primary/90"
                          >
                            View Details
                          </button>
                        </div>
                      </div>
                      
                      {recording.summary && (
                        <p className="mt-3 text-sm text-secondary line-clamp-2">
                          {recording.summary}
                        </p>
                      )}
                      
                      {recording.topics?.length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-2">
                          {recording.topics.slice(0, 5).map((topic, i) => (
                            <span key={i} className="px-2 py-0.5 bg-slate-100 rounded text-xs text-secondary">
                              {topic}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Coaching Tab */}
        {activeTab === 'coaching' && analytics && (
          <div className="space-y-6">
            <div className="bg-white rounded-xl border border-border p-6">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Lightbulb className="w-5 h-5 text-yellow-500" />
                AI Coaching Insights
              </h3>
              <p className="text-secondary mb-6">
                Based on analysis of your recent calls, here are personalized improvement suggestions:
              </p>
              
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
            </div>

            {/* Talk Ratio Guidance */}
            <div className="bg-white rounded-xl border border-border p-6">
              <h3 className="text-lg font-semibold mb-4">Talk Ratio Analysis</h3>
              <div className="flex items-center gap-6">
                <div className="relative w-32 h-32">
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
                      <div className="w-3 h-3 bg-yellow-500 rounded-full" />
                      <span>Your avg: {analytics.overview.avg_talk_ratio}%</span>
                    </div>
                  </div>
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
              <div className="p-8 text-center text-secondary">
                <Users className="w-12 h-12 mx-auto mb-3 opacity-30" />
                <p>No team data available yet.</p>
              </div>
            ) : (
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
            )}
          </div>
        )}

        {/* Recording Detail Modal */}
        {selectedRecording && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="bg-white rounded-2xl shadow-xl max-w-3xl w-full max-h-[80vh] overflow-y-auto"
            >
              <div className="p-6 border-b border-border flex items-center justify-between">
                <h3 className="text-lg font-semibold">Call Analysis</h3>
                <button
                  onClick={() => setSelectedRecording(null)}
                  className="p-2 hover:bg-slate-100 rounded-lg"
                >
                  ✕
                </button>
              </div>
              
              <div className="p-6 space-y-6">
                {/* Summary */}
                {selectedRecording.summary && (
                  <div>
                    <h4 className="font-medium text-foreground mb-2">Summary</h4>
                    <p className="text-secondary">{selectedRecording.summary}</p>
                  </div>
                )}

                {/* Key Moments */}
                {selectedRecording.key_moments?.length > 0 && (
                  <div>
                    <h4 className="font-medium text-foreground mb-2">Key Moments</h4>
                    <div className="space-y-2">
                      {selectedRecording.key_moments.map((moment, i) => (
                        <div key={i} className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg">
                          <div className={`w-6 h-6 rounded-full flex items-center justify-center ${
                            moment.type === 'commitment' ? 'bg-green-100' : 'bg-blue-100'
                          }`}>
                            {moment.type === 'commitment' ? (
                              <CheckCircle className="w-4 h-4 text-green-600" />
                            ) : (
                              <MessageSquare className="w-4 h-4 text-blue-600" />
                            )}
                          </div>
                          <div>
                            <p className="text-sm text-foreground">{moment.text}</p>
                            <p className="text-xs text-secondary mt-1">{moment.timestamp}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Action Items */}
                {selectedRecording.action_items?.length > 0 && (
                  <div>
                    <h4 className="font-medium text-foreground mb-2">Action Items</h4>
                    <ul className="space-y-2">
                      {selectedRecording.action_items.map((item, i) => (
                        <li key={i} className="flex items-center gap-2 text-sm">
                          <Target className="w-4 h-4 text-primary" />
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Coaching Tips */}
                {selectedRecording.coaching_tips?.length > 0 && (
                  <div>
                    <h4 className="font-medium text-foreground mb-2">Coaching Tips</h4>
                    <div className="space-y-2">
                      {selectedRecording.coaching_tips.map((tip, i) => (
                        <div key={i} className="flex items-start gap-2 p-3 bg-yellow-50 rounded-lg">
                          <Lightbulb className="w-4 h-4 text-yellow-600 mt-0.5" />
                          <p className="text-sm text-yellow-800">{tip}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Transcription */}
                {selectedRecording.transcription && (
                  <div>
                    <h4 className="font-medium text-foreground mb-2">Transcription</h4>
                    <div className="max-h-48 overflow-y-auto p-4 bg-slate-50 rounded-lg">
                      <p className="text-sm text-secondary whitespace-pre-wrap">
                        {selectedRecording.transcription}
                      </p>
                    </div>
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

export default CallAnalyticsDashboard;
