import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, X, TrendingUp, Target, Zap, ChevronRight } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const AICoach = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [insights, setInsights] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen && insights.length === 0) {
      fetchInsights();
    }
  }, [isOpen]);

  const fetchInsights = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_URL}/api/insights`);
      setInsights(response.data);
    } catch (error) {
      console.error('Failed to load AI insights');
    } finally {
      setLoading(false);
    }
  };

  const getInsightIcon = (type) => {
    switch (type) {
      case 'hot_leads':
        return <Target className="w-5 h-5" />;
      case 'follow_up_needed':
        return <Zap className="w-5 h-5" />;
      case 'performance':
        return <TrendingUp className="w-5 h-5" />;
      default:
        return <Sparkles className="w-5 h-5" />;
    }
  };

  return (
    <>
      {/* Floating Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-6 right-6 w-14 h-14 bg-accent text-white rounded-full shadow-2xl hover:scale-110 transition-transform duration-200 flex items-center justify-center z-50 ai-card"
      >
        <Sparkles className="w-6 h-6" />
      </button>

      {/* AI Coach Panel */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className="fixed bottom-24 right-6 w-96 bg-white rounded-xl shadow-2xl border border-border overflow-hidden z-50"
          >
            {/* Header */}
            <div className="bg-gradient-to-r from-accent to-primary p-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-white" />
                <h3 className="text-white font-semibold">AI Sales Coach</h3>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="text-white/80 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Content */}
            <div className="p-4 max-h-96 overflow-y-auto">
              {loading ? (
                <div className="text-center py-8">
                  <div className="animate-spin w-8 h-8 border-3 border-accent border-t-transparent rounded-full mx-auto"></div>
                  <p className="text-sm text-secondary mt-3">Analyzing your pipeline...</p>
                </div>
              ) : insights.length > 0 ? (
                <div className="space-y-3">
                  {insights.map((insight, index) => (
                    <motion.div
                      key={index}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.1 }}
                      className="bg-slate-50 p-4 rounded-lg border border-border"
                    >
                      <div className="flex items-start gap-3">
                        <div className="w-8 h-8 bg-accent/10 text-accent rounded-lg flex items-center justify-center flex-shrink-0">
                          {getInsightIcon(insight.insight_type)}
                        </div>
                        <div className="flex-1">
                          <p className="text-sm font-medium text-foreground mb-2">{insight.message}</p>
                          {insight.action_items && insight.action_items.length > 0 && (
                            <div className="space-y-1">
                              {insight.action_items.map((item, i) => (
                                <div key={i} className="flex items-center gap-2 text-xs text-secondary">
                                  <ChevronRight className="w-3 h-3" />
                                  {item}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <Sparkles className="w-12 h-12 text-secondary mx-auto mb-3" />
                  <p className="text-sm text-secondary">No new insights right now</p>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="border-t border-border p-3 bg-slate-50">
              <button
                onClick={fetchInsights}
                className="w-full py-2 text-sm font-medium text-primary hover:bg-primary/10 rounded-lg transition-colors"
              >
                Refresh Insights
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};

export default AICoach;
