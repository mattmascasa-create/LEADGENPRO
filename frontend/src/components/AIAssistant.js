import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { 
  MessageCircle, X, Send, Bot, User, Sparkles, 
  HelpCircle, BookOpen, Phone, Mail, Calendar, 
  Target, Users, TrendingUp, Lightbulb, ChevronRight,
  Clock, AlertCircle, CheckCircle, ArrowRight, Zap,
  BarChart2, PhoneCall, FileText, Rocket
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const quickActions = [
  { icon: HelpCircle, label: 'How do I add a lead?', query: 'How do I add a new lead to the system?' },
  { icon: Phone, label: 'Making calls', query: 'How do I make calls to leads using the VoIP feature?' },
  { icon: Calendar, label: 'Schedule meetings', query: 'How do I schedule meetings with prospects?' },
  { icon: Target, label: 'Pipeline stages', query: 'Explain the different pipeline stages and when to move leads between them.' },
  { icon: TrendingUp, label: 'Improve conversion', query: 'What are best practices to improve my lead conversion rate?' },
  { icon: BookOpen, label: 'Platform overview', query: 'Give me a quick overview of all the features in LeadGen Pro.' }
];

// AI-powered suggestions that update based on context
const getSmartSuggestions = (stats, currentPage) => {
  const suggestions = [];
  
  // Time-based suggestions
  const hour = new Date().getHours();
  if (hour >= 9 && hour <= 11) {
    suggestions.push({
      type: 'timing',
      icon: Clock,
      title: 'Prime Call Time',
      description: 'Morning hours have 23% higher connect rates. Start dialing!',
      action: 'Start Calling',
      link: '/call-lists',
      priority: 'high'
    });
  } else if (hour >= 14 && hour <= 16) {
    suggestions.push({
      type: 'timing',
      icon: Mail,
      title: 'Email Sweet Spot',
      description: 'Afternoon emails get 18% more opens. Send follow-ups now.',
      action: 'Open AI Email',
      link: '/ai-email',
      priority: 'medium'
    });
  }

  // Stats-based suggestions
  if (stats?.leads_needing_followup > 0) {
    suggestions.push({
      type: 'action',
      icon: AlertCircle,
      title: `${stats.leads_needing_followup} Leads Need Follow-up`,
      description: 'These leads haven\'t been contacted in 3+ days. Reach out today!',
      action: 'View Leads',
      link: '/leads',
      priority: 'high'
    });
  }

  if (stats?.hot_leads > 0) {
    suggestions.push({
      type: 'opportunity',
      icon: Zap,
      title: `${stats.hot_leads} Hot Leads Detected`,
      description: 'High-score leads ready for immediate outreach. Don\'t let them go cold!',
      action: 'Prioritize Now',
      link: '/pipeline',
      priority: 'high'
    });
  }

  if (stats?.tasks_due_today > 0) {
    suggestions.push({
      type: 'task',
      icon: CheckCircle,
      title: `${stats.tasks_due_today} Tasks Due Today`,
      description: 'Stay on top of your commitments to keep deals moving.',
      action: 'View Tasks',
      link: '/tasks',
      priority: 'medium'
    });
  }

  if (stats?.meetings_today > 0) {
    suggestions.push({
      type: 'meeting',
      icon: Calendar,
      title: `${stats.meetings_today} Meetings Today`,
      description: 'Prepare talking points and review lead history before calls.',
      action: 'View Calendar',
      link: '/calendar',
      priority: 'medium'
    });
  }

  // Learning suggestions
  suggestions.push({
    type: 'tip',
    icon: Lightbulb,
    title: 'Pro Tip: Use Call Analytics',
    description: 'Review your call recordings with AI analysis to improve your pitch.',
    action: 'Explore',
    link: '/call-analytics',
    priority: 'low'
  });

  return suggestions.slice(0, 4); // Max 4 suggestions
};

const AIAssistant = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('chat'); // 'chat' | 'insights'
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: "👋 Hi! I'm your LeadGen Pro AI Coach. I can help you navigate the platform, answer questions, and suggest your next best actions. What would you like to do?"
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [smartSuggestions, setSmartSuggestions] = useState([]);
  const [stats, setStats] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  useEffect(() => {
    if (isOpen) {
      fetchStatsForSuggestions();
    }
  }, [isOpen]);

  const fetchStatsForSuggestions = async () => {
    try {
      const [statsRes, leadsRes, tasksRes] = await Promise.all([
        axios.get(`${API_URL}/api/stats`),
        axios.get(`${API_URL}/api/leads`),
        axios.get(`${API_URL}/api/tasks`)
      ]);

      const leads = leadsRes.data || [];
      const tasks = tasksRes.data || [];
      const today = new Date();
      today.setHours(0, 0, 0, 0);

      const computedStats = {
        total_leads: leads.length,
        hot_leads: leads.filter(l => l.score >= 80 && l.stage === 'prospecting').length,
        leads_needing_followup: leads.filter(l => {
          if (!l.last_contacted) return true;
          const lastContact = new Date(l.last_contacted);
          const daysSince = (Date.now() - lastContact.getTime()) / (1000 * 60 * 60 * 24);
          return daysSince > 3;
        }).length,
        tasks_due_today: tasks.filter(t => {
          if (t.completed) return false;
          const dueDate = new Date(t.due_date);
          dueDate.setHours(0, 0, 0, 0);
          return dueDate.getTime() === today.getTime();
        }).length,
        meetings_today: 0, // Would come from calendar API
        ...statsRes.data
      };

      setStats(computedStats);
      setSmartSuggestions(getSmartSuggestions(computedStats, window.location.pathname));
    } catch (error) {
      console.error('Failed to fetch stats for suggestions');
      setSmartSuggestions(getSmartSuggestions({}, window.location.pathname));
    }
  };

  const handleSend = async (query = input) => {
    if (!query.trim()) return;

    const userMessage = { role: 'user', content: query };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await axios.post(`${API_URL}/api/assistant/chat`, {
        message: query,
        context: 'platform_help'
      });

      const assistantMessage = {
        role: 'assistant',
        content: response.data.response
      };
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage = {
        role: 'assistant',
        content: "I apologize, but I'm having trouble connecting right now. Please try again in a moment."
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickAction = (query) => {
    handleSend(query);
  };

  const handleSuggestionClick = (suggestion) => {
    if (suggestion.link) {
      window.location.href = suggestion.link;
      setIsOpen(false);
    }
  };

  const priorityColors = {
    high: 'border-red-200 bg-red-50',
    medium: 'border-yellow-200 bg-yellow-50',
    low: 'border-blue-200 bg-blue-50'
  };

  const priorityIcons = {
    high: 'text-red-600',
    medium: 'text-yellow-600',
    low: 'text-blue-600'
  };

  return (
    <>
      {/* Floating Button - Positioned above Team Chat on right side */}
      <motion.button
        onClick={() => setIsOpen(true)}
        className={`fixed bottom-44 right-6 z-40 w-14 h-14 bg-gradient-to-br from-slate-800 to-slate-900 rounded-2xl shadow-2xl flex items-center justify-center text-white hover:shadow-slate-500/30 hover:scale-105 transition-all border border-slate-700 ${isOpen ? 'hidden' : ''}`}
        whileHover={{ scale: 1.08 }}
        whileTap={{ scale: 0.95 }}
        data-testid="ai-assistant-btn"
      >
        <div className="relative">
          <Sparkles className="w-6 h-6" />
          {smartSuggestions.filter(s => s.priority === 'high').length > 0 && (
            <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full text-xs flex items-center justify-center animate-pulse border-2 border-slate-900">
              {smartSuggestions.filter(s => s.priority === 'high').length}
            </span>
          )}
        </div>
      </motion.button>

      {/* Chat Window */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            className="fixed bottom-8 left-6 z-50 w-[420px] h-[580px] bg-slate-900 rounded-2xl shadow-2xl flex flex-col overflow-hidden border border-slate-700"
            data-testid="ai-assistant-panel"
          >
            {/* Header */}
            <div className="bg-gradient-to-r from-slate-800 to-slate-700 p-4 text-white border-b border-slate-600">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg">
                    <Sparkles className="w-6 h-6" />
                  </div>
                  <div>
                    <h3 className="font-semibold">AI Sales Coach</h3>
                    <p className="text-xs text-slate-400">Your productivity assistant</p>
                  </div>
                </div>
                <button
                  onClick={() => setIsOpen(false)}
                  className="p-2 hover:bg-slate-600 rounded-lg transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              
              {/* Tabs */}
              <div className="flex gap-2">
                <button
                  onClick={() => setActiveTab('chat')}
                  className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
                    activeTab === 'chat' 
                      ? 'bg-blue-600 text-white' 
                      : 'bg-slate-700/50 text-slate-300 hover:bg-slate-700'
                  }`}
                >
                  <MessageCircle className="w-4 h-4 inline mr-1" />
                  Chat
                </button>
                <button
                  onClick={() => setActiveTab('insights')}
                  className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors relative ${
                    activeTab === 'insights' 
                      ? 'bg-blue-600 text-white' 
                      : 'bg-slate-700/50 text-slate-300 hover:bg-slate-700'
                  }`}
                >
                  <Rocket className="w-4 h-4 inline mr-1" />
                  Next Actions
                  {smartSuggestions.filter(s => s.priority === 'high').length > 0 && (
                    <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full text-xs flex items-center justify-center">
                      {smartSuggestions.filter(s => s.priority === 'high').length}
                    </span>
                  )}
                </button>
              </div>
            </div>

            {activeTab === 'chat' ? (
              <>
                {/* Messages */}
                <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-800">
                  {messages.map((msg, idx) => (
                    <motion.div
                      key={idx}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
                    >
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                        msg.role === 'user' ? 'bg-blue-600 text-white' : 'bg-slate-700 text-purple-400'
                      }`}>
                        {msg.role === 'user' ? <User className="w-4 h-4" /> : <Sparkles className="w-4 h-4" />}
                      </div>
                      <div className={`max-w-[80%] p-3 rounded-xl ${
                        msg.role === 'user' 
                          ? 'bg-blue-600 text-white rounded-tr-sm' 
                          : 'bg-slate-700 text-slate-100 rounded-tl-sm'
                      }`}>
                        <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                      </div>
                    </motion.div>
                  ))}
                  {isLoading && (
                    <div className="flex gap-3">
                      <div className="w-8 h-8 bg-slate-700 rounded-lg flex items-center justify-center">
                        <Sparkles className="w-4 h-4 text-purple-400" />
                      </div>
                      <div className="bg-slate-700 p-3 rounded-xl rounded-tl-sm">
                        <div className="flex gap-1">
                          <span className="w-2 h-2 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                          <span className="w-2 h-2 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                          <span className="w-2 h-2 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                        </div>
                      </div>
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </div>

                {/* Quick Actions */}
                {messages.length <= 2 && (
                  <div className="p-3 border-t border-slate-700 bg-slate-800">
                    <p className="text-xs text-slate-400 mb-2 flex items-center gap-1">
                      <Lightbulb className="w-3 h-3" />
                      Quick questions:
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {quickActions.slice(0, 4).map((action, idx) => (
                        <button
                          key={idx}
                          onClick={() => handleQuickAction(action.query)}
                          className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg text-xs font-medium transition-colors flex items-center gap-1"
                        >
                          <action.icon className="w-3 h-3" />
                          {action.label}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Input */}
                <div className="p-4 border-t border-slate-700 bg-slate-900">
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      handleSend();
                    }}
                    className="flex gap-2"
                  >
                    <input
                      ref={inputRef}
                      type="text"
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      placeholder="Ask me anything..."
                      className="flex-1 px-4 py-2 bg-slate-800 border border-slate-600 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm text-white placeholder-slate-400"
                      disabled={isLoading}
                    />
                    <button
                      type="submit"
                      disabled={!input.trim() || isLoading}
                      className="w-10 h-10 bg-blue-600 text-white rounded-xl flex items-center justify-center hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      <Send className="w-4 h-4" />
                    </button>
                  </form>
                </div>
              </>
            ) : (
              /* Insights/Next Actions Tab */
              <div className="flex-1 overflow-y-auto p-4 bg-slate-800">
                <div className="mb-4">
                  <h4 className="text-white font-semibold mb-1">Your Next Best Actions</h4>
                  <p className="text-xs text-slate-400">AI-powered suggestions to boost your productivity</p>
                </div>

                <div className="space-y-3">
                  {smartSuggestions.map((suggestion, idx) => {
                    const Icon = suggestion.icon;
                    return (
                      <motion.button
                        key={idx}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: idx * 0.1 }}
                        onClick={() => handleSuggestionClick(suggestion)}
                        className={`w-full p-4 rounded-xl border-2 text-left transition-all hover:scale-[1.02] ${priorityColors[suggestion.priority]}`}
                      >
                        <div className="flex items-start gap-3">
                          <div className={`w-10 h-10 rounded-lg flex items-center justify-center bg-white shadow-sm ${priorityIcons[suggestion.priority]}`}>
                            <Icon className="w-5 h-5" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between mb-1">
                              <h5 className="font-semibold text-slate-900 text-sm">{suggestion.title}</h5>
                              {suggestion.priority === 'high' && (
                                <span className="px-2 py-0.5 bg-red-500 text-white text-xs rounded-full">Urgent</span>
                              )}
                            </div>
                            <p className="text-xs text-slate-600 mb-2">{suggestion.description}</p>
                            <span className="inline-flex items-center gap-1 text-xs font-medium text-blue-600">
                              {suggestion.action}
                              <ArrowRight className="w-3 h-3" />
                            </span>
                          </div>
                        </div>
                      </motion.button>
                    );
                  })}
                </div>

                {/* Quick Stats */}
                {stats && (
                  <div className="mt-6 p-4 bg-slate-700/50 rounded-xl">
                    <h5 className="text-white font-medium mb-3 text-sm">Today's Snapshot</h5>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="text-center p-2 bg-slate-800 rounded-lg">
                        <p className="text-2xl font-bold text-white">{stats.total_leads || 0}</p>
                        <p className="text-xs text-slate-400">Total Leads</p>
                      </div>
                      <div className="text-center p-2 bg-slate-800 rounded-lg">
                        <p className="text-2xl font-bold text-yellow-400">{stats.hot_leads || 0}</p>
                        <p className="text-xs text-slate-400">Hot Leads</p>
                      </div>
                      <div className="text-center p-2 bg-slate-800 rounded-lg">
                        <p className="text-2xl font-bold text-red-400">{stats.leads_needing_followup || 0}</p>
                        <p className="text-xs text-slate-400">Need Follow-up</p>
                      </div>
                      <div className="text-center p-2 bg-slate-800 rounded-lg">
                        <p className="text-2xl font-bold text-green-400">{stats.tasks_due_today || 0}</p>
                        <p className="text-xs text-slate-400">Tasks Today</p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Motivational tip */}
                <div className="mt-4 p-3 bg-gradient-to-r from-blue-600/20 to-purple-600/20 rounded-xl border border-blue-500/30">
                  <p className="text-xs text-slate-300 flex items-start gap-2">
                    <Lightbulb className="w-4 h-4 text-yellow-400 flex-shrink-0 mt-0.5" />
                    <span><strong>Pro tip:</strong> The best salespeople follow up within 5 minutes. Speed wins deals!</span>
                  </p>
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};

export default AIAssistant;
