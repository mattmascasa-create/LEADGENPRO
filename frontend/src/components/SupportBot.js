import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  MessageCircle, X, Send, Bot, User, Loader2, 
  AlertTriangle, CheckCircle, ChevronDown, Wrench,
  Sparkles, RefreshCw
} from 'lucide-react';
import axios from 'axios';
import { toast } from 'react-toastify';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const SupportBot = ({ currentError = null }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [hasUnresolvedError, setHasUnresolvedError] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (currentError) {
      setHasUnresolvedError(true);
      // Auto-open for critical errors
      if (currentError.severity === 'critical') {
        setIsOpen(true);
        handleErrorAnalysis(currentError);
      }
    }
  }, [currentError]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleErrorAnalysis = async (error) => {
    setLoading(true);
    
    // Add system message
    setMessages(prev => [...prev, {
      type: 'system',
      content: `Analyzing error: ${error.error_type || error.message}`,
      timestamp: new Date()
    }]);

    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(
        `${API_URL}/api/support-bot/diagnose`,
        {
          error_id: error.id,
          question: `Analyze this error: ${error.message || error.error_type}`,
          context: { page: window.location.pathname }
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      const diagnosis = response.data;
      
      setMessages(prev => [...prev, {
        type: 'bot',
        content: diagnosis.diagnosis,
        diagnosis: diagnosis,
        timestamp: new Date()
      }]);

      if (diagnosis.fix_steps?.length > 0) {
        setMessages(prev => [...prev, {
          type: 'bot',
          content: 'Here are the steps to fix this issue:',
          steps: diagnosis.fix_steps,
          timestamp: new Date()
        }]);
      }

      if (diagnosis.can_auto_fix) {
        setMessages(prev => [...prev, {
          type: 'action',
          content: 'I can try to fix this automatically. Would you like me to try?',
          error_id: error.id,
          timestamp: new Date()
        }]);
      }

    } catch (err) {
      setMessages(prev => [...prev, {
        type: 'bot',
        content: 'I encountered an issue analyzing the error. Please try again or contact support.',
        timestamp: new Date()
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput('');
    
    setMessages(prev => [...prev, {
      type: 'user',
      content: userMessage,
      timestamp: new Date()
    }]);

    setLoading(true);

    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(
        `${API_URL}/api/support-bot/diagnose`,
        {
          question: userMessage,
          context: { page: window.location.pathname }
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      const diagnosis = response.data;
      
      setMessages(prev => [...prev, {
        type: 'bot',
        content: diagnosis.diagnosis,
        diagnosis: diagnosis,
        timestamp: new Date()
      }]);

      if (diagnosis.fix_steps?.length > 0) {
        setMessages(prev => [...prev, {
          type: 'bot',
          steps: diagnosis.fix_steps,
          timestamp: new Date()
        }]);
      }

    } catch (err) {
      setMessages(prev => [...prev, {
        type: 'bot',
        content: 'Sorry, I had trouble processing your request. Please try again.',
        timestamp: new Date()
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleAutoFix = async (errorId) => {
    setLoading(true);
    
    setMessages(prev => [...prev, {
      type: 'system',
      content: 'Attempting automatic fix...',
      timestamp: new Date()
    }]);

    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(
        `${API_URL}/api/support-bot/auto-fix/${errorId}`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );

      if (response.data.success) {
        setMessages(prev => [...prev, {
          type: 'bot',
          content: `✅ Auto-fix successful! ${response.data.message}`,
          success: true,
          timestamp: new Date()
        }]);
        setHasUnresolvedError(false);
        toast.success('Issue automatically resolved!');
      } else {
        setMessages(prev => [...prev, {
          type: 'bot',
          content: `Could not auto-fix: ${response.data.message}`,
          timestamp: new Date()
        }]);
        
        if (response.data.manual_steps?.length > 0) {
          setMessages(prev => [...prev, {
            type: 'bot',
            content: 'Here are manual steps to resolve the issue:',
            steps: response.data.manual_steps,
            timestamp: new Date()
          }]);
        }
      }

    } catch (err) {
      setMessages(prev => [...prev, {
        type: 'bot',
        content: 'Auto-fix failed. Please try the manual steps or contact support.',
        timestamp: new Date()
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Floating Button */}
      <motion.button
        onClick={() => setIsOpen(true)}
        className={`fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full shadow-lg flex items-center justify-center transition-colors ${
          hasUnresolvedError 
            ? 'bg-red-500 hover:bg-red-600 animate-pulse' 
            : 'bg-primary hover:bg-primary/90'
        }`}
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.9 }}
      >
        {hasUnresolvedError ? (
          <AlertTriangle className="w-6 h-6 text-white" />
        ) : (
          <Bot className="w-6 h-6 text-white" />
        )}
      </motion.button>

      {/* Chat Window */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            className="fixed bottom-24 right-6 z-50 w-96 max-w-[calc(100vw-3rem)] bg-white rounded-2xl shadow-2xl border border-border overflow-hidden"
          >
            {/* Header */}
            <div className="bg-gradient-to-r from-primary to-accent p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center">
                  <Sparkles className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="text-white font-semibold">AI Support Bot</h3>
                  <p className="text-white/70 text-xs">Powered by AI diagnostics</p>
                </div>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="text-white/70 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Messages */}
            <div className="h-80 overflow-y-auto p-4 space-y-4 bg-slate-50">
              {messages.length === 0 && (
                <div className="text-center py-8">
                  <Bot className="w-12 h-12 text-primary/30 mx-auto mb-3" />
                  <p className="text-secondary text-sm">
                    Hi! I&apos;m your AI support assistant. I can help diagnose issues and suggest fixes.
                  </p>
                  <p className="text-secondary/70 text-xs mt-2">
                    Ask me anything or I&apos;ll analyze errors automatically.
                  </p>
                </div>
              )}

              {messages.map((msg, idx) => (
                <div key={idx} className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}>
                  {msg.type === 'system' ? (
                    <div className="flex items-center gap-2 text-xs text-secondary bg-white px-3 py-2 rounded-lg">
                      <RefreshCw className="w-3 h-3 animate-spin" />
                      {msg.content}
                    </div>
                  ) : msg.type === 'action' ? (
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 max-w-[85%]">
                      <p className="text-sm text-blue-800 mb-2">{msg.content}</p>
                      <button
                        onClick={() => handleAutoFix(msg.error_id)}
                        disabled={loading}
                        className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50"
                      >
                        <Wrench className="w-4 h-4" />
                        Auto-Fix
                      </button>
                    </div>
                  ) : (
                    <div className={`max-w-[85%] rounded-lg p-3 ${
                      msg.type === 'user' 
                        ? 'bg-primary text-white' 
                        : msg.success 
                          ? 'bg-green-50 border border-green-200 text-green-800'
                          : 'bg-white border border-border'
                    }`}>
                      {msg.content && <p className="text-sm">{msg.content}</p>}
                      
                      {msg.steps && (
                        <ol className="mt-2 space-y-1.5">
                          {msg.steps.map((step, i) => (
                            <li key={i} className="flex items-start gap-2 text-sm">
                              <span className="flex-shrink-0 w-5 h-5 bg-primary/10 text-primary rounded-full flex items-center justify-center text-xs font-medium">
                                {i + 1}
                              </span>
                              <span className="text-foreground">{step}</span>
                            </li>
                          ))}
                        </ol>
                      )}

                      {msg.diagnosis?.prevention && (
                        <div className="mt-2 pt-2 border-t border-border/50">
                          <p className="text-xs text-secondary">
                            <strong>Prevention:</strong> {msg.diagnosis.prevention}
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}

              {loading && (
                <div className="flex justify-start">
                  <div className="bg-white border border-border rounded-lg p-3">
                    <div className="flex items-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin text-primary" />
                      <span className="text-sm text-secondary">Analyzing...</span>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="p-4 border-t border-border bg-white">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                  placeholder="Describe your issue..."
                  className="flex-1 px-4 py-2 text-sm border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  disabled={loading}
                />
                <button
                  onClick={handleSend}
                  disabled={!input.trim() || loading}
                  className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-50 transition-colors"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};

export default SupportBot;
