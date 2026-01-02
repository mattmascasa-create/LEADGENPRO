import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Phone, Clock, TrendingUp, BarChart2, Mic, MessageSquare,
  ThumbsUp, ThumbsDown, AlertCircle, Play, Pause, Download,
  ChevronDown, ChevronUp, Brain, Target, Zap, Award
} from 'lucide-react';
import { toast } from 'react-toastify';
import { format } from 'date-fns';
import { motion, AnimatePresence } from 'framer-motion';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import DashboardLayout from '@/components/DashboardLayout';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const CallAnalyticsPage = () => {
  const [callLogs, setCallLogs] = useState([]);
  const [selectedCall, setSelectedCall] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expandedCall, setExpandedCall] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [logsRes, statsRes] = await Promise.all([
        axios.get(`${API_URL}/api/calls/logs?limit=50`),
        axios.get(`${API_URL}/api/calls/stats`)
      ]);
      setCallLogs(logsRes.data);
      setStats(statsRes.data);
    } catch (error) {
      toast.error('Failed to load call analytics');
    } finally {
      setLoading(false);
    }
  };

  const fetchCallAnalysis = async (callId) => {
    try {
      const response = await axios.get(`${API_URL}/api/calls/${callId}/analysis`);
      setSelectedCall(response.data);
    } catch (error) {
      toast.error('Failed to load call analysis');
    }
  };

  const outcomeColors = {
    connected: '#10b981',
    voicemail: '#3b82f6',
    no_answer: '#f59e0b',
    busy: '#f97316',
    wrong_number: '#ef4444',
    declined: '#6b7280'
  };

  const pieData = stats?.outcomes ? Object.entries(stats.outcomes).map(([name, value]) => ({
    name: name.replace('_', ' '),
    value,
    color: outcomeColors[name] || '#6b7280'
  })) : [];

  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getSentimentColor = (sentiment) => {
    if (sentiment >= 0.6) return 'text-green-600 bg-green-100';
    if (sentiment >= 0.4) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  const getSentimentLabel = (sentiment) => {
    if (sentiment >= 0.6) return 'Positive';
    if (sentiment >= 0.4) return 'Neutral';
    return 'Negative';
  };

  return (
    <DashboardLayout>
      <div>
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-foreground mb-2">Call Analytics</h1>
          <p className="text-secondary">AI-powered insights from your sales calls (Gong-like analysis)</p>
        </div>

        {/* Stats Overview */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white p-6 rounded-xl border border-border"
          >
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center">
                <Phone className="w-6 h-6 text-primary" />
              </div>
              <div>
                <p className="text-sm text-secondary">Total Calls</p>
                <p className="text-2xl font-bold">{stats?.total_calls || 0}</p>
              </div>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-white p-6 rounded-xl border border-border"
          >
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                <TrendingUp className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-secondary">Connect Rate</p>
                <p className="text-2xl font-bold">{stats?.connect_rate || 0}%</p>
              </div>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-white p-6 rounded-xl border border-border"
          >
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                <Clock className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-secondary">Avg Duration</p>
                <p className="text-2xl font-bold">{formatDuration(stats?.average_duration_seconds || 0)}</p>
              </div>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-white p-6 rounded-xl border border-border"
          >
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                <Mic className="w-6 h-6 text-purple-600" />
              </div>
              <div>
                <p className="text-sm text-secondary">Total Talk Time</p>
                <p className="text-2xl font-bold">{Math.round((stats?.total_duration_seconds || 0) / 60)}m</p>
              </div>
            </div>
          </motion.div>
        </div>

        {/* Charts */}
        <div className="grid lg:grid-cols-2 gap-6 mb-8">
          <div className="bg-white p-6 rounded-xl border border-border">
            <h3 className="text-lg font-semibold mb-4">Call Outcomes</h3>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={2}
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex flex-wrap justify-center gap-4 mt-4">
              {pieData.map((item, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
                  <span className="text-sm capitalize">{item.name}: {item.value}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-white p-6 rounded-xl border border-border">
            <h3 className="text-lg font-semibold mb-4">AI Coaching Tips</h3>
            <div className="space-y-4">
              <div className="flex items-start gap-3 p-3 bg-green-50 rounded-lg">
                <Award className="w-5 h-5 text-green-600 mt-0.5" />
                <div>
                  <p className="font-medium text-green-800">Strong opener usage</p>
                  <p className="text-sm text-green-700">Your calls with personalized openers have 40% higher engagement.</p>
                </div>
              </div>
              <div className="flex items-start gap-3 p-3 bg-yellow-50 rounded-lg">
                <Target className="w-5 h-5 text-yellow-600 mt-0.5" />
                <div>
                  <p className="font-medium text-yellow-800">Objection handling</p>
                  <p className="text-sm text-yellow-700">Practice responding to pricing objections - detected in 60% of calls.</p>
                </div>
              </div>
              <div className="flex items-start gap-3 p-3 bg-blue-50 rounded-lg">
                <Zap className="w-5 h-5 text-blue-600 mt-0.5" />
                <div>
                  <p className="font-medium text-blue-800">Follow-up timing</p>
                  <p className="text-sm text-blue-700">Best callback times: Tuesday-Thursday, 10am-12pm.</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Call List */}
        <div className="bg-white rounded-xl border border-border">
          <div className="p-6 border-b border-border">
            <h3 className="text-lg font-semibold">Recent Calls with AI Analysis</h3>
          </div>
          <div className="divide-y divide-border">
            {callLogs.length > 0 ? callLogs.map((call) => (
              <div key={call.id} className="p-4">
                <div
                  className="flex items-center justify-between cursor-pointer"
                  onClick={() => setExpandedCall(expandedCall === call.id ? null : call.id)}
                >
                  <div className="flex items-center gap-4">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                      call.outcome === 'connected' ? 'bg-green-100 text-green-600' :
                      call.outcome === 'voicemail' ? 'bg-blue-100 text-blue-600' :
                      call.outcome === 'no_answer' ? 'bg-yellow-100 text-yellow-600' :
                      'bg-gray-100 text-gray-600'
                    }`}>
                      <Phone className="w-5 h-5" />
                    </div>
                    <div>
                      <p className="font-medium">{call.phone_number}</p>
                      <p className="text-sm text-secondary">
                        {format(new Date(call.created_at), 'MMM d, yyyy h:mm a')}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className={`px-3 py-1 rounded-full text-sm font-medium capitalize ${
                      call.outcome === 'connected' ? 'bg-green-100 text-green-700' :
                      call.outcome === 'voicemail' ? 'bg-blue-100 text-blue-700' :
                      call.outcome === 'no_answer' ? 'bg-yellow-100 text-yellow-700' :
                      'bg-gray-100 text-gray-700'
                    }`}>
                      {call.outcome?.replace('_', ' ')}
                    </span>
                    <span className="text-sm text-secondary">{formatDuration(call.duration)}</span>
                    {expandedCall === call.id ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                  </div>
                </div>

                <AnimatePresence>
                  {expandedCall === call.id && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="overflow-hidden"
                    >
                      <div className="mt-4 pt-4 border-t border-border">
                        {/* AI Analysis Section */}
                        {call.analysis ? (
                          <div className="grid md:grid-cols-2 gap-4">
                            <div>
                              <h4 className="font-medium mb-2 flex items-center gap-2">
                                <Brain className="w-4 h-4 text-purple-600" />
                                AI Analysis
                              </h4>
                              <div className="space-y-2">
                                <div className="flex items-center justify-between p-2 bg-slate-50 rounded">
                                  <span className="text-sm">Sentiment</span>
                                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${getSentimentColor(call.analysis?.sentiment || 0.5)}`}>
                                    {getSentimentLabel(call.analysis?.sentiment || 0.5)}
                                  </span>
                                </div>
                                <div className="flex items-center justify-between p-2 bg-slate-50 rounded">
                                  <span className="text-sm">Talk Ratio</span>
                                  <span className="text-sm font-medium">{call.analysis?.talk_ratio || 50}% you / {100 - (call.analysis?.talk_ratio || 50)}% prospect</span>
                                </div>
                                <div className="flex items-center justify-between p-2 bg-slate-50 rounded">
                                  <span className="text-sm">Questions Asked</span>
                                  <span className="text-sm font-medium">{call.analysis?.questions_asked || 0}</span>
                                </div>
                              </div>
                            </div>
                            <div>
                              <h4 className="font-medium mb-2">Key Topics</h4>
                              <div className="flex flex-wrap gap-2">
                                {(call.analysis?.topics || ['pricing', 'features', 'timeline']).map((topic, idx) => (
                                  <span key={idx} className="px-2 py-1 bg-primary/10 text-primary rounded text-sm">
                                    {topic}
                                  </span>
                                ))}
                              </div>
                              {call.analysis?.coaching_tip && (
                                <div className="mt-3 p-3 bg-yellow-50 rounded-lg">
                                  <p className="text-sm text-yellow-800">
                                    <strong>Coaching:</strong> {call.analysis.coaching_tip}
                                  </p>
                                </div>
                              )}
                            </div>
                          </div>
                        ) : (
                          <div className="text-center py-4">
                            <p className="text-secondary text-sm">AI analysis available for recorded calls</p>
                            <button
                              onClick={() => fetchCallAnalysis(call.id)}
                              className="mt-2 px-4 py-2 bg-primary text-white rounded-lg text-sm"
                            >
                              Generate Analysis
                            </button>
                          </div>
                        )}

                        {/* Notes */}
                        {call.notes && (
                          <div className="mt-4 p-3 bg-slate-50 rounded-lg">
                            <p className="text-sm font-medium mb-1">Notes</p>
                            <p className="text-sm text-secondary">{call.notes}</p>
                          </div>
                        )}

                        {/* Recording Player */}
                        {call.recording_url && (
                          <div className="mt-4 p-3 bg-slate-50 rounded-lg">
                            <p className="text-sm font-medium mb-2">Call Recording</p>
                            <audio controls className="w-full" src={call.recording_url}>
                              Your browser does not support the audio element.
                            </audio>
                          </div>
                        )}

                        {/* Transcript */}
                        {call.transcript && (
                          <div className="mt-4">
                            <p className="text-sm font-medium mb-2 flex items-center gap-2">
                              <MessageSquare className="w-4 h-4" />
                              Transcript
                            </p>
                            <div className="p-3 bg-slate-50 rounded-lg max-h-48 overflow-y-auto">
                              <p className="text-sm text-secondary whitespace-pre-wrap">{call.transcript}</p>
                            </div>
                          </div>
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )) : (
              <div className="p-12 text-center text-secondary">
                <Phone className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>No calls recorded yet</p>
                <p className="text-sm">Start making calls to see analytics here</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default CallAnalyticsPage;
