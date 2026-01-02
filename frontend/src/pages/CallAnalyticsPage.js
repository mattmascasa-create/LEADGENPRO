import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Phone, Clock, TrendingUp, BarChart2, Mic, MessageSquare,
  ThumbsUp, ThumbsDown, AlertCircle, Play, Pause, Download,
  ChevronDown, ChevronUp, Brain, Target, Zap, Award, FileText,
  Loader2, CheckCircle, XCircle, HelpCircle, ArrowRight
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
  const [transcribing, setTranscribing] = useState({});
  const [analyzing, setAnalyzing] = useState({});

  useEffect(() => {
    fetchData();
  }, []);

  const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return { headers: { Authorization: `Bearer ${token}` } };
  };

  const fetchData = async () => {
    try {
      const [logsRes, statsRes] = await Promise.all([
        axios.get(`${API_URL}/api/calls/logs?limit=50`, getAuthHeaders()),
        axios.get(`${API_URL}/api/calls/stats`, getAuthHeaders())
      ]);
      setCallLogs(logsRes.data);
      setStats(statsRes.data);
    } catch (error) {
      toast.error('Failed to load call analytics');
    } finally {
      setLoading(false);
    }
  };

  const transcribeCall = async (callId) => {
    setTranscribing(prev => ({ ...prev, [callId]: true }));
    try {
      const response = await axios.post(
        `${API_URL}/api/calls/${callId}/transcribe`,
        {},
        getAuthHeaders()
      );
      
      if (response.data.success) {
        toast.success(response.data.already_transcribed ? 'Transcript loaded' : 'Call transcribed successfully!');
        // Update the call in state
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
        getAuthHeaders()
      );
      
      if (response.data.success) {
        toast.success('AI analysis complete!');
        // Update the call in state
        setCallLogs(prev => prev.map(call => 
          call.id === callId 
            ? { ...call, analysis: response.data.analysis }
            : call
        ));
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to analyze call');
    } finally {
      setAnalyzing(prev => ({ ...prev, [callId]: false }));
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

  const getScoreColor = (score) => {
    if (score >= 80) return 'text-green-600 bg-green-100';
    if (score >= 60) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
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

  const renderDetailedAnalysis = (analysis) => {
    if (!analysis || typeof analysis !== 'object') return null;
    
    // Check if this is the new detailed format
    const isDetailedFormat = analysis.overall_score !== undefined;
    
    if (!isDetailedFormat) {
      // Legacy simple format
      return (
        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <h4 className="font-medium mb-2 flex items-center gap-2">
              <Brain className="w-4 h-4 text-purple-600" />
              AI Analysis
            </h4>
            <div className="space-y-2">
              <div className="flex items-center justify-between p-2 bg-slate-50 rounded">
                <span className="text-sm">Sentiment</span>
                <span className={`px-2 py-0.5 rounded text-xs font-medium ${getSentimentColor(analysis?.sentiment || 0.5)}`}>
                  {getSentimentLabel(analysis?.sentiment || 0.5)}
                </span>
              </div>
              <div className="flex items-center justify-between p-2 bg-slate-50 rounded">
                <span className="text-sm">Talk Ratio</span>
                <span className="text-sm font-medium">{analysis?.talk_ratio || 50}% you</span>
              </div>
            </div>
          </div>
          <div>
            {analysis?.coaching_tip && (
              <div className="p-3 bg-yellow-50 rounded-lg">
                <p className="text-sm text-yellow-800">
                  <strong>Coaching:</strong> {analysis.coaching_tip}
                </p>
              </div>
            )}
          </div>
        </div>
      );
    }

    // New detailed Gong-like format
    return (
      <div className="space-y-6">
        {/* Overall Score */}
        <div className="flex items-center gap-4">
          <div className={`w-16 h-16 rounded-full flex items-center justify-center text-xl font-bold ${getScoreColor(analysis.overall_score)}`}>
            {analysis.overall_score}
          </div>
          <div>
            <h4 className="font-semibold text-lg">Overall Call Score</h4>
            <p className="text-secondary text-sm">{analysis.call_summary}</p>
          </div>
        </div>

        {/* Key Metrics Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {/* Sentiment */}
          <div className="bg-slate-50 p-4 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              {analysis.sentiment?.overall >= 0.6 ? (
                <ThumbsUp className="w-4 h-4 text-green-600" />
              ) : analysis.sentiment?.overall < 0.4 ? (
                <ThumbsDown className="w-4 h-4 text-red-600" />
              ) : (
                <HelpCircle className="w-4 h-4 text-yellow-600" />
              )}
              <span className="text-sm font-medium">Sentiment</span>
            </div>
            <p className={`text-lg font-bold ${getSentimentColor(analysis.sentiment?.overall || 0.5).split(' ')[0]}`}>
              {getSentimentLabel(analysis.sentiment?.overall || 0.5)}
            </p>
            <p className="text-xs text-secondary">
              Customer: {getSentimentLabel(analysis.sentiment?.customer || 0.5)}
            </p>
          </div>

          {/* Talk Ratio */}
          <div className="bg-slate-50 p-4 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <Mic className="w-4 h-4 text-blue-600" />
              <span className="text-sm font-medium">Talk Ratio</span>
            </div>
            <p className="text-lg font-bold">{analysis.talk_ratio?.rep_percentage || 50}%</p>
            <p className="text-xs text-secondary capitalize">
              {analysis.talk_ratio?.assessment?.replace('_', ' ') || 'balanced'}
            </p>
          </div>

          {/* Questions */}
          <div className="bg-slate-50 p-4 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <HelpCircle className="w-4 h-4 text-purple-600" />
              <span className="text-sm font-medium">Questions</span>
            </div>
            <p className="text-lg font-bold">{analysis.questions?.total_asked || 0}</p>
            <p className="text-xs text-secondary">
              {analysis.questions?.open_ended || 0} open-ended
            </p>
          </div>

          {/* Next Steps */}
          <div className="bg-slate-50 p-4 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <ArrowRight className="w-4 h-4 text-green-600" />
              <span className="text-sm font-medium">Next Steps</span>
            </div>
            <p className="text-lg font-bold flex items-center gap-1">
              {analysis.next_steps?.mentioned ? (
                <><CheckCircle className="w-4 h-4 text-green-600" /> Set</>
              ) : (
                <><XCircle className="w-4 h-4 text-red-600" /> Missing</>
              )}
            </p>
            <p className="text-xs text-secondary">
              {analysis.next_steps?.clear ? 'Clear & specific' : 'Needs clarity'}
            </p>
          </div>
        </div>

        {/* Key Topics */}
        <div>
          <h4 className="font-medium mb-2">Key Topics Discussed</h4>
          <div className="flex flex-wrap gap-2">
            {(analysis.key_topics || []).map((topic, idx) => (
              <span key={idx} className="px-3 py-1 bg-primary/10 text-primary rounded-full text-sm">
                {topic}
              </span>
            ))}
          </div>
        </div>

        {/* Customer Signals */}
        {(analysis.customer_signals?.buying_signals?.length > 0 || 
          analysis.customer_signals?.objections?.length > 0 || 
          analysis.customer_signals?.concerns?.length > 0) && (
          <div className="grid md:grid-cols-3 gap-4">
            {analysis.customer_signals?.buying_signals?.length > 0 && (
              <div className="bg-green-50 p-4 rounded-lg">
                <h5 className="font-medium text-green-800 mb-2 flex items-center gap-2">
                  <ThumbsUp className="w-4 h-4" /> Buying Signals
                </h5>
                <ul className="text-sm text-green-700 space-y-1">
                  {analysis.customer_signals.buying_signals.map((signal, idx) => (
                    <li key={idx}>• {signal}</li>
                  ))}
                </ul>
              </div>
            )}
            {analysis.customer_signals?.objections?.length > 0 && (
              <div className="bg-red-50 p-4 rounded-lg">
                <h5 className="font-medium text-red-800 mb-2 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4" /> Objections
                </h5>
                <ul className="text-sm text-red-700 space-y-1">
                  {analysis.customer_signals.objections.map((obj, idx) => (
                    <li key={idx}>• {obj}</li>
                  ))}
                </ul>
              </div>
            )}
            {analysis.customer_signals?.concerns?.length > 0 && (
              <div className="bg-yellow-50 p-4 rounded-lg">
                <h5 className="font-medium text-yellow-800 mb-2 flex items-center gap-2">
                  <HelpCircle className="w-4 h-4" /> Concerns
                </h5>
                <ul className="text-sm text-yellow-700 space-y-1">
                  {analysis.customer_signals.concerns.map((concern, idx) => (
                    <li key={idx}>• {concern}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Coaching Insights */}
        <div className="bg-gradient-to-r from-purple-50 to-blue-50 p-5 rounded-xl border border-purple-100">
          <h4 className="font-semibold mb-3 flex items-center gap-2">
            <Brain className="w-5 h-5 text-purple-600" />
            AI Coaching Insights
          </h4>
          <div className="grid md:grid-cols-2 gap-4 mb-4">
            <div>
              <h5 className="text-sm font-medium text-green-700 mb-2">Strengths</h5>
              <ul className="text-sm space-y-1">
                {(analysis.coaching_insights?.strengths || []).map((s, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <CheckCircle className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                    <span>{s}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h5 className="text-sm font-medium text-orange-700 mb-2">Areas to Improve</h5>
              <ul className="text-sm space-y-1">
                {(analysis.coaching_insights?.improvements || []).map((i, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <Target className="w-4 h-4 text-orange-600 mt-0.5 flex-shrink-0" />
                    <span>{i}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
          {analysis.coaching_insights?.priority_action && (
            <div className="bg-white p-3 rounded-lg border border-purple-200">
              <p className="text-sm">
                <strong className="text-purple-700">Priority Action:</strong>{' '}
                {analysis.coaching_insights.priority_action}
              </p>
            </div>
          )}
        </div>

        {/* Next Steps Items */}
        {analysis.next_steps?.items?.length > 0 && (
          <div className="bg-blue-50 p-4 rounded-lg">
            <h4 className="font-medium text-blue-800 mb-2">Follow-up Items</h4>
            <ul className="text-sm text-blue-700 space-y-1">
              {analysis.next_steps.items.map((item, idx) => (
                <li key={idx} className="flex items-center gap-2">
                  <ArrowRight className="w-4 h-4" /> {item}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  };

  return (
    <DashboardLayout>
      <div data-testid="call-analytics-page">
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
            <p className="text-sm text-secondary mt-1">Click on a call to view transcript and Gong-style AI analysis</p>
          </div>
          <div className="divide-y divide-border">
            {callLogs.length > 0 ? callLogs.map((call) => (
              <div key={call.id} className="p-4" data-testid={`call-row-${call.id}`}>
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
                      <div className="mt-4 pt-4 border-t border-border space-y-4">
                        {/* Action Buttons */}
                        <div className="flex flex-wrap gap-3">
                          {call.recording_url && !call.transcript && (
                            <button
                              onClick={(e) => { e.stopPropagation(); transcribeCall(call.id); }}
                              disabled={transcribing[call.id]}
                              className="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 disabled:opacity-50 flex items-center gap-2"
                              data-testid={`transcribe-btn-${call.id}`}
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
                            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
                            data-testid={`analyze-btn-${call.id}`}
                          >
                            {analyzing[call.id] ? (
                              <><Loader2 className="w-4 h-4 animate-spin" /> Analyzing...</>
                            ) : (
                              <><Brain className="w-4 h-4" /> {call.analysis ? 'Re-analyze' : 'AI Analysis'}</>
                            )}
                          </button>
                        </div>

                        {/* Recording Player */}
                        {call.recording_url && (
                          <div className="p-4 bg-slate-50 rounded-lg">
                            <p className="text-sm font-medium mb-2 flex items-center gap-2">
                              <Mic className="w-4 h-4" /> Call Recording
                            </p>
                            <audio controls className="w-full" src={call.recording_url}>
                              Your browser does not support the audio element.
                            </audio>
                          </div>
                        )}

                        {/* Transcript */}
                        {call.transcript && (
                          <div className="p-4 bg-slate-50 rounded-lg">
                            <p className="text-sm font-medium mb-2 flex items-center gap-2">
                              <MessageSquare className="w-4 h-4" />
                              Transcript
                            </p>
                            <div className="max-h-48 overflow-y-auto bg-white p-3 rounded border border-slate-200">
                              <p className="text-sm whitespace-pre-wrap">{call.transcript}</p>
                            </div>
                          </div>
                        )}

                        {/* AI Analysis */}
                        {call.analysis && (
                          <div className="p-4 bg-white rounded-lg border border-slate-200">
                            {renderDetailedAnalysis(call.analysis)}
                          </div>
                        )}

                        {/* Notes */}
                        {call.notes && (
                          <div className="p-3 bg-slate-50 rounded-lg">
                            <p className="text-sm font-medium mb-1">Notes</p>
                            <p className="text-sm text-secondary">{call.notes}</p>
                          </div>
                        )}

                        {/* No recording message */}
                        {!call.recording_url && (
                          <div className="text-center py-4 text-secondary">
                            <Mic className="w-8 h-8 mx-auto mb-2 opacity-50" />
                            <p className="text-sm">No recording available for this call</p>
                            <p className="text-xs">Enable recording to get AI transcription and analysis</p>
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
