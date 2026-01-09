import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  TrendingUp, DollarSign, Target, AlertTriangle, CheckCircle,
  Calendar, Users, BarChart3, RefreshCw, ChevronRight, Eye,
  Clock, ArrowUpRight, ArrowDownRight, Filter, Loader2
} from 'lucide-react';
import axios from 'axios';
import { toast } from 'react-toastify';
import { format } from 'date-fns';
import DashboardLayout from '@/components/DashboardLayout';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, Legend, ComposedChart, Area
} from 'recharts';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const COLORS = ['#10B981', '#3B82F6', '#F59E0B', '#8B5CF6', '#EF4444', '#6B7280'];

const STAGE_COLORS = {
  new: '#6B7280',
  contacted: '#3B82F6',
  qualified: '#8B5CF6',
  proposal: '#F59E0B',
  negotiation: '#10B981',
  won: '#059669',
  lost: '#EF4444'
};

const PipelineForecastPage = () => {
  const [forecast, setForecast] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedDeal, setSelectedDeal] = useState(null);
  const [dealAnalysis, setDealAnalysis] = useState(null);
  const [analyzingDeal, setAnalyzingDeal] = useState(false);

  const getAuthHeaders = () => ({
    Authorization: `Bearer ${localStorage.getItem('token')}`
  });

  useEffect(() => {
    fetchForecast();
  }, []);

  const fetchForecast = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_URL}/api/forecasting/pipeline`, {
        headers: getAuthHeaders()
      });
      setForecast(response.data);
    } catch (error) {
      console.error('Error fetching forecast:', error);
      toast.error('Failed to load pipeline forecast');
    } finally {
      setLoading(false);
    }
  };

  const analyzeDeal = async (leadId) => {
    setAnalyzingDeal(true);
    setDealAnalysis(null);
    try {
      const response = await axios.post(
        `${API_URL}/api/forecasting/analyze-deal/${leadId}`,
        {},
        { headers: getAuthHeaders() }
      );
      setDealAnalysis(response.data);
    } catch (error) {
      toast.error('Failed to analyze deal');
    } finally {
      setAnalyzingDeal(false);
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-96">
          <RefreshCw className="w-8 h-8 animate-spin text-primary" />
        </div>
      </DashboardLayout>
    );
  }

  const stageChartData = forecast?.stage_distribution?.map(s => ({
    name: s.stage.charAt(0).toUpperCase() + s.stage.slice(1),
    value: s.weighted,
    count: s.count,
    total: s.value,
    fill: STAGE_COLORS[s.stage] || '#6B7280'
  })) || [];

  return (
    <DashboardLayout>
      <div className="p-4 lg:p-6">
        {/* Header */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl lg:text-4xl font-bold text-foreground mb-1 flex items-center gap-3">
              <TrendingUp className="w-8 h-8 text-primary" />
              Pipeline Forecast
            </h1>
            <p className="text-sm lg:text-base text-secondary">
              AI-powered revenue predictions and deal insights
            </p>
          </div>
          
          <button
            onClick={fetchForecast}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-border rounded-lg hover:bg-slate-50"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh Forecast
          </button>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-gradient-to-br from-blue-500 to-blue-600 p-5 rounded-xl text-white"
          >
            <div className="flex items-center gap-2 mb-2 opacity-80">
              <DollarSign className="w-5 h-5" />
              <span className="text-sm">Total Pipeline</span>
            </div>
            <p className="text-3xl font-bold">{formatCurrency(forecast?.summary?.total_pipeline || 0)}</p>
            <p className="text-sm opacity-80 mt-1">{forecast?.summary?.total_deals || 0} deals</p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-gradient-to-br from-green-500 to-green-600 p-5 rounded-xl text-white"
          >
            <div className="flex items-center gap-2 mb-2 opacity-80">
              <Target className="w-5 h-5" />
              <span className="text-sm">Weighted Pipeline</span>
            </div>
            <p className="text-3xl font-bold">{formatCurrency(forecast?.summary?.weighted_pipeline || 0)}</p>
            <p className="text-sm opacity-80 mt-1">{forecast?.summary?.avg_probability || 0}% avg probability</p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-gradient-to-br from-purple-500 to-purple-600 p-5 rounded-xl text-white"
          >
            <div className="flex items-center gap-2 mb-2 opacity-80">
              <Calendar className="w-5 h-5" />
              <span className="text-sm">Monthly Forecast</span>
            </div>
            <p className="text-3xl font-bold">{formatCurrency(forecast?.summary?.monthly_forecast || 0)}</p>
            <p className="text-sm opacity-80 mt-1">Expected this month</p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-gradient-to-br from-orange-500 to-orange-600 p-5 rounded-xl text-white"
          >
            <div className="flex items-center gap-2 mb-2 opacity-80">
              <BarChart3 className="w-5 h-5" />
              <span className="text-sm">Quarterly Forecast</span>
            </div>
            <p className="text-3xl font-bold">{formatCurrency(forecast?.summary?.quarterly_forecast || 0)}</p>
            <p className="text-sm opacity-80 mt-1">Expected this quarter</p>
          </motion.div>
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Stage Distribution Chart */}
          <div className="lg:col-span-2 bg-white rounded-xl border border-border p-6">
            <h3 className="font-semibold mb-4">Pipeline by Stage</h3>
            <ResponsiveContainer width="100%" height={300}>
              <ComposedChart data={stageChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis 
                  yAxisId="left" 
                  tick={{ fontSize: 12 }} 
                  tickFormatter={(v) => `$${(v/1000).toFixed(0)}k`}
                />
                <YAxis 
                  yAxisId="right" 
                  orientation="right" 
                  tick={{ fontSize: 12 }}
                />
                <Tooltip 
                  formatter={(value, name) => {
                    if (name === 'Weighted Value') return formatCurrency(value);
                    if (name === 'Total Value') return formatCurrency(value);
                    return value;
                  }}
                />
                <Legend />
                <Bar yAxisId="left" dataKey="value" name="Weighted Value" radius={[4, 4, 0, 0]}>
                  {stageChartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Bar>
                <Line yAxisId="right" type="monotone" dataKey="count" name="Deal Count" stroke="#8B5CF6" strokeWidth={2} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          {/* Probability Distribution */}
          <div className="bg-white rounded-xl border border-border p-6">
            <h3 className="font-semibold mb-4">Deal Probability Distribution</h3>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={stageChartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={2}
                  dataKey="value"
                >
                  {stageChartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => formatCurrency(value)} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Deal Lists */}
        <div className="grid lg:grid-cols-2 gap-6 mt-6">
          {/* Top Deals */}
          <div className="bg-white rounded-xl border border-border overflow-hidden">
            <div className="p-4 border-b border-border flex items-center justify-between">
              <h3 className="font-semibold flex items-center gap-2">
                <ArrowUpRight className="w-5 h-5 text-green-500" />
                Top Opportunities
              </h3>
            </div>
            <div className="divide-y divide-border max-h-96 overflow-y-auto">
              {forecast?.top_deals?.map((deal) => (
                <div
                  key={deal.lead_id}
                  className="p-4 hover:bg-slate-50 cursor-pointer transition-colors"
                  onClick={() => {
                    setSelectedDeal(deal);
                    analyzeDeal(deal.lead_id);
                  }}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-foreground">{deal.lead_name || 'Unknown'}</p>
                      <p className="text-sm text-secondary">{deal.company || 'No company'}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-foreground">{formatCurrency(deal.deal_value)}</p>
                      <div className="flex items-center gap-2 justify-end">
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                          deal.probability >= 60 ? 'bg-green-100 text-green-700' :
                          deal.probability >= 40 ? 'bg-yellow-100 text-yellow-700' :
                          'bg-red-100 text-red-700'
                        }`}>
                          {deal.probability}%
                        </span>
                        <span className="text-xs text-secondary capitalize">{deal.stage}</span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* At Risk Deals */}
          <div className="bg-white rounded-xl border border-border overflow-hidden">
            <div className="p-4 border-b border-border flex items-center justify-between">
              <h3 className="font-semibold flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-red-500" />
                At Risk Deals
              </h3>
            </div>
            <div className="divide-y divide-border max-h-96 overflow-y-auto">
              {forecast?.at_risk_deals?.length === 0 ? (
                <div className="p-8 text-center text-secondary">
                  <CheckCircle className="w-12 h-12 mx-auto mb-3 text-green-500 opacity-50" />
                  <p>No at-risk deals!</p>
                  <p className="text-sm">All your deals are in good standing</p>
                </div>
              ) : (
                forecast?.at_risk_deals?.map((deal) => (
                  <div
                    key={deal.lead_id}
                    className="p-4 hover:bg-slate-50 cursor-pointer transition-colors"
                    onClick={() => {
                      setSelectedDeal(deal);
                      analyzeDeal(deal.lead_id);
                    }}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-foreground">{deal.lead_name || 'Unknown'}</p>
                        <p className="text-sm text-secondary">{deal.company || 'No company'}</p>
                      </div>
                      <div className="text-right">
                        <p className="font-bold text-foreground">{formatCurrency(deal.deal_value)}</p>
                        <div className="flex items-center gap-2 justify-end">
                          <span className="px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-700">
                            {deal.probability}%
                          </span>
                          {deal.last_contacted && (
                            <span className="text-xs text-red-500 flex items-center gap-1">
                              <Clock className="w-3 h-3" />
                              Stale
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Deal Analysis Modal */}
        {selectedDeal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="bg-white rounded-2xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
            >
              <div className="p-6 border-b border-border flex items-center justify-between sticky top-0 bg-white">
                <div>
                  <h3 className="text-lg font-semibold">Deal Analysis</h3>
                  <p className="text-sm text-secondary">{selectedDeal.lead_name}</p>
                </div>
                <button
                  onClick={() => {
                    setSelectedDeal(null);
                    setDealAnalysis(null);
                  }}
                  className="p-2 hover:bg-slate-100 rounded-lg"
                >
                  ×
                </button>
              </div>

              <div className="p-6">
                {analyzingDeal ? (
                  <div className="flex items-center justify-center py-12">
                    <Loader2 className="w-8 h-8 animate-spin text-primary" />
                    <span className="ml-3 text-secondary">Analyzing deal...</span>
                  </div>
                ) : dealAnalysis ? (
                  <div className="space-y-6">
                    {/* Score Overview */}
                    <div className="grid grid-cols-2 gap-4">
                      <div className="p-4 bg-gradient-to-br from-blue-50 to-blue-100 rounded-xl">
                        <p className="text-sm text-blue-600 mb-1">Close Probability</p>
                        <p className={`text-4xl font-bold ${
                          dealAnalysis.analysis.close_probability >= 60 ? 'text-green-600' :
                          dealAnalysis.analysis.close_probability >= 40 ? 'text-yellow-600' :
                          'text-red-600'
                        }`}>
                          {dealAnalysis.analysis.close_probability}%
                        </p>
                      </div>
                      <div className="p-4 bg-gradient-to-br from-purple-50 to-purple-100 rounded-xl">
                        <p className="text-sm text-purple-600 mb-1">Engagement Score</p>
                        <p className="text-4xl font-bold text-purple-700">
                          {dealAnalysis.analysis.engagement_score}
                        </p>
                      </div>
                    </div>

                    {/* Activity Stats */}
                    <div className="grid grid-cols-3 gap-4">
                      <div className="text-center p-3 bg-slate-50 rounded-lg">
                        <p className="text-2xl font-bold">{dealAnalysis.analysis.activity_count}</p>
                        <p className="text-xs text-secondary">Activities</p>
                      </div>
                      <div className="text-center p-3 bg-slate-50 rounded-lg">
                        <p className="text-2xl font-bold">{dealAnalysis.analysis.call_count}</p>
                        <p className="text-xs text-secondary">Calls</p>
                      </div>
                      <div className="text-center p-3 bg-slate-50 rounded-lg">
                        <p className="text-2xl font-bold">{dealAnalysis.analysis.emails_opened}/{dealAnalysis.analysis.email_count}</p>
                        <p className="text-xs text-secondary">Emails Opened</p>
                      </div>
                    </div>

                    {/* Confidence Factors */}
                    {dealAnalysis.analysis.confidence_factors.length > 0 && (
                      <div>
                        <h4 className="font-medium mb-2 flex items-center gap-2 text-green-700">
                          <CheckCircle className="w-4 h-4" />
                          Confidence Factors
                        </h4>
                        <div className="space-y-2">
                          {dealAnalysis.analysis.confidence_factors.map((factor, i) => (
                            <div key={i} className="flex items-center gap-2 text-sm text-green-600 bg-green-50 px-3 py-2 rounded-lg">
                              <CheckCircle className="w-4 h-4" />
                              {factor}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Risk Factors */}
                    {dealAnalysis.analysis.risk_factors.length > 0 && (
                      <div>
                        <h4 className="font-medium mb-2 flex items-center gap-2 text-red-700">
                          <AlertTriangle className="w-4 h-4" />
                          Risk Factors
                        </h4>
                        <div className="space-y-2">
                          {dealAnalysis.analysis.risk_factors.map((factor, i) => (
                            <div key={i} className="flex items-center gap-2 text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">
                              <AlertTriangle className="w-4 h-4" />
                              {factor}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Recommendation */}
                    <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl">
                      <h4 className="font-medium text-blue-800 mb-2">AI Recommendation</h4>
                      <p className="text-blue-700">{dealAnalysis.analysis.recommendation}</p>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-12 text-secondary">
                    <Target className="w-12 h-12 mx-auto mb-3 opacity-30" />
                    <p>Click a deal to see AI analysis</p>
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

export default PipelineForecastPage;
