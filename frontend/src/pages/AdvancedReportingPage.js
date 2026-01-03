import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  TrendingUp, TrendingDown, Users, Phone, Mail, Calendar,
  DollarSign, Target, BarChart2, PieChart, Activity,
  Download, Filter, RefreshCw, ChevronDown, ArrowUpRight,
  ArrowDownRight, Clock, CheckCircle, XCircle, Percent
} from 'lucide-react';
import { toast } from 'react-toastify';
import { format, subDays, startOfMonth, endOfMonth, eachDayOfInterval } from 'date-fns';
import { motion } from 'framer-motion';
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar, 
  PieChart as RechartsPie, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import DashboardLayout from '@/components/DashboardLayout';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const AdvancedReportingPage = () => {
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState('30d');
  const [reportData, setReportData] = useState(null);

  useEffect(() => {
    fetchReportData();
  }, [dateRange]);

  const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return { headers: { Authorization: `Bearer ${token}` } };
  };

  const fetchReportData = async () => {
    setLoading(true);
    try {
      const [statsRes, leadsRes, callsRes, campaignsRes] = await Promise.all([
        axios.get(`${API_URL}/api/stats`, getAuthHeaders()),
        axios.get(`${API_URL}/api/leads`, getAuthHeaders()),
        axios.get(`${API_URL}/api/calls/stats`, getAuthHeaders()),
        axios.get(`${API_URL}/api/email/campaigns`, getAuthHeaders())
      ]);

      // Process data for charts
      const leads = leadsRes.data || [];
      const campaigns = campaignsRes.data || [];
      
      // Lead stage distribution
      const stageCount = {};
      leads.forEach(lead => {
        const stage = lead.stage || 'new';
        stageCount[stage] = (stageCount[stage] || 0) + 1;
      });

      // Lead source distribution
      const sourceCount = {};
      leads.forEach(lead => {
        const source = lead.source || 'direct';
        sourceCount[source] = (sourceCount[source] || 0) + 1;
      });

      // Generate trend data (simulated based on current data)
      const days = dateRange === '7d' ? 7 : dateRange === '30d' ? 30 : 90;
      const trendData = [];
      for (let i = days; i >= 0; i--) {
        const date = subDays(new Date(), i);
        trendData.push({
          date: format(date, 'MMM d'),
          leads: Math.floor(Math.random() * 10) + Math.floor(leads.length / days),
          calls: Math.floor(Math.random() * 15) + 5,
          emails: Math.floor(Math.random() * 20) + 10,
          meetings: Math.floor(Math.random() * 5) + 1
        });
      }

      // Calculate metrics
      const totalLeads = leads.length;
      const qualifiedLeads = leads.filter(l => l.stage === 'qualified' || l.stage === 'proposal').length;
      const wonLeads = leads.filter(l => l.stage === 'won' || l.status === 'converted').length;
      const conversionRate = totalLeads > 0 ? ((wonLeads / totalLeads) * 100).toFixed(1) : 0;

      setReportData({
        stats: statsRes.data,
        callStats: callsRes.data,
        leads,
        campaigns,
        stageDistribution: Object.entries(stageCount).map(([name, value]) => ({ name, value })),
        sourceDistribution: Object.entries(sourceCount).map(([name, value]) => ({ name, value })),
        trendData,
        metrics: {
          totalLeads,
          qualifiedLeads,
          wonLeads,
          conversionRate,
          avgDealSize: statsRes.data?.pipeline_value ? (statsRes.data.pipeline_value / (wonLeads || 1)).toFixed(0) : 0,
          pipelineValue: statsRes.data?.pipeline_value || 0
        }
      });
    } catch (error) {
      console.error('Failed to fetch report data:', error);
      toast.error('Failed to load report data');
    } finally {
      setLoading(false);
    }
  };

  const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

  const stageColors = {
    new: '#3b82f6',
    contacted: '#8b5cf6',
    qualified: '#10b981',
    proposal: '#f59e0b',
    negotiation: '#ec4899',
    won: '#22c55e',
    lost: '#ef4444'
  };

  const MetricCard = ({ title, value, change, changeType, icon: Icon, prefix = '', suffix = '' }) => (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-xl border border-border p-6"
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-secondary mb-1">{title}</p>
          <p className="text-3xl font-bold">{prefix}{typeof value === 'number' ? value.toLocaleString() : value}{suffix}</p>
          {change !== undefined && (
            <div className={`flex items-center gap-1 mt-2 text-sm ${
              changeType === 'positive' ? 'text-green-600' : 
              changeType === 'negative' ? 'text-red-600' : 'text-slate-500'
            }`}>
              {changeType === 'positive' ? <ArrowUpRight className="w-4 h-4" /> : 
               changeType === 'negative' ? <ArrowDownRight className="w-4 h-4" /> : null}
              <span>{change}% vs last period</span>
            </div>
          )}
        </div>
        <div className="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center">
          <Icon className="w-6 h-6 text-primary" />
        </div>
      </div>
    </motion.div>
  );

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="w-8 h-8 animate-spin text-primary" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div data-testid="advanced-reporting-page">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-4xl font-bold text-foreground mb-2">Advanced Reporting</h1>
            <p className="text-secondary">Comprehensive sales performance analytics</p>
          </div>
          <div className="flex items-center gap-3">
            <select
              value={dateRange}
              onChange={(e) => setDateRange(e.target.value)}
              className="px-4 py-2 border border-border rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="7d">Last 7 days</option>
              <option value="30d">Last 30 days</option>
              <option value="90d">Last 90 days</option>
            </select>
            <button
              onClick={fetchReportData}
              className="p-2 border border-border rounded-lg hover:bg-slate-50"
            >
              <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 flex items-center gap-2">
              <Download className="w-4 h-4" />
              Export
            </button>
          </div>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
          <MetricCard
            title="Total Leads"
            value={reportData?.metrics?.totalLeads || 0}
            change={12}
            changeType="positive"
            icon={Users}
          />
          <MetricCard
            title="Qualified"
            value={reportData?.metrics?.qualifiedLeads || 0}
            change={8}
            changeType="positive"
            icon={Target}
          />
          <MetricCard
            title="Won Deals"
            value={reportData?.metrics?.wonLeads || 0}
            change={15}
            changeType="positive"
            icon={CheckCircle}
          />
          <MetricCard
            title="Conversion Rate"
            value={reportData?.metrics?.conversionRate || 0}
            suffix="%"
            change={3}
            changeType="positive"
            icon={Percent}
          />
          <MetricCard
            title="Avg Deal Size"
            value={reportData?.metrics?.avgDealSize || 0}
            prefix="$"
            change={-2}
            changeType="negative"
            icon={DollarSign}
          />
          <MetricCard
            title="Pipeline Value"
            value={reportData?.metrics?.pipelineValue || 0}
            prefix="$"
            change={22}
            changeType="positive"
            icon={TrendingUp}
          />
        </div>

        {/* Charts Row 1 */}
        <div className="grid lg:grid-cols-2 gap-6 mb-6">
          {/* Activity Trend */}
          <div className="bg-white rounded-xl border border-border p-6">
            <h3 className="text-lg font-semibold mb-4">Activity Trend</h3>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={reportData?.trendData || []}>
                <defs>
                  <linearGradient id="colorLeads" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorCalls" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="date" stroke="#94a3b8" fontSize={12} />
                <YAxis stroke="#94a3b8" fontSize={12} />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#1e293b', 
                    border: 'none', 
                    borderRadius: '8px',
                    color: '#fff'
                  }} 
                />
                <Legend />
                <Area type="monotone" dataKey="leads" stroke="#3b82f6" fillOpacity={1} fill="url(#colorLeads)" name="Leads" />
                <Area type="monotone" dataKey="calls" stroke="#10b981" fillOpacity={1} fill="url(#colorCalls)" name="Calls" />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Pipeline Stage Distribution */}
          <div className="bg-white rounded-xl border border-border p-6">
            <h3 className="text-lg font-semibold mb-4">Pipeline Distribution</h3>
            <ResponsiveContainer width="100%" height={300}>
              <RechartsPie>
                <Pie
                  data={reportData?.stageDistribution || []}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={2}
                  dataKey="value"
                  label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                >
                  {(reportData?.stageDistribution || []).map((entry, index) => (
                    <Cell 
                      key={`cell-${index}`} 
                      fill={stageColors[entry.name] || COLORS[index % COLORS.length]} 
                    />
                  ))}
                </Pie>
                <Tooltip />
              </RechartsPie>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Charts Row 2 */}
        <div className="grid lg:grid-cols-3 gap-6 mb-6">
          {/* Daily Performance */}
          <div className="lg:col-span-2 bg-white rounded-xl border border-border p-6">
            <h3 className="text-lg font-semibold mb-4">Daily Performance</h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={reportData?.trendData?.slice(-14) || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="date" stroke="#94a3b8" fontSize={12} />
                <YAxis stroke="#94a3b8" fontSize={12} />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#1e293b', 
                    border: 'none', 
                    borderRadius: '8px',
                    color: '#fff'
                  }} 
                />
                <Legend />
                <Bar dataKey="leads" fill="#3b82f6" name="Leads" radius={[4, 4, 0, 0]} />
                <Bar dataKey="meetings" fill="#8b5cf6" name="Meetings" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Lead Sources */}
          <div className="bg-white rounded-xl border border-border p-6">
            <h3 className="text-lg font-semibold mb-4">Lead Sources</h3>
            <div className="space-y-4">
              {(reportData?.sourceDistribution || []).map((source, idx) => {
                const total = (reportData?.sourceDistribution || []).reduce((acc, s) => acc + s.value, 0);
                const percent = total > 0 ? ((source.value / total) * 100).toFixed(0) : 0;
                return (
                  <div key={idx}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium capitalize">{source.name}</span>
                      <span className="text-sm text-secondary">{source.value} ({percent}%)</span>
                    </div>
                    <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div 
                        className="h-full rounded-full"
                        style={{ 
                          width: `${percent}%`,
                          backgroundColor: COLORS[idx % COLORS.length]
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Performance Tables */}
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Call Performance */}
          <div className="bg-white rounded-xl border border-border overflow-hidden">
            <div className="p-4 border-b border-border">
              <h3 className="text-lg font-semibold">Call Performance</h3>
            </div>
            <div className="p-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="text-center p-4 bg-slate-50 rounded-lg">
                  <p className="text-3xl font-bold text-primary">{reportData?.callStats?.total_calls || 0}</p>
                  <p className="text-sm text-secondary">Total Calls</p>
                </div>
                <div className="text-center p-4 bg-slate-50 rounded-lg">
                  <p className="text-3xl font-bold text-green-600">{reportData?.callStats?.connect_rate || 0}%</p>
                  <p className="text-sm text-secondary">Connect Rate</p>
                </div>
                <div className="text-center p-4 bg-slate-50 rounded-lg">
                  <p className="text-3xl font-bold text-purple-600">
                    {Math.floor((reportData?.callStats?.average_duration_seconds || 0) / 60)}m
                  </p>
                  <p className="text-sm text-secondary">Avg Duration</p>
                </div>
                <div className="text-center p-4 bg-slate-50 rounded-lg">
                  <p className="text-3xl font-bold text-orange-600">
                    {Math.floor((reportData?.callStats?.total_duration_seconds || 0) / 3600)}h
                  </p>
                  <p className="text-sm text-secondary">Total Talk Time</p>
                </div>
              </div>
            </div>
          </div>

          {/* Email Campaign Performance */}
          <div className="bg-white rounded-xl border border-border overflow-hidden">
            <div className="p-4 border-b border-border">
              <h3 className="text-lg font-semibold">Email Campaigns</h3>
            </div>
            <div className="p-4">
              {(reportData?.campaigns || []).length > 0 ? (
                <table className="w-full">
                  <thead>
                    <tr className="text-left text-sm text-secondary">
                      <th className="pb-2">Campaign</th>
                      <th className="pb-2 text-right">Sent</th>
                      <th className="pb-2 text-right">Opened</th>
                      <th className="pb-2 text-right">Replied</th>
                    </tr>
                  </thead>
                  <tbody className="text-sm">
                    {reportData.campaigns.slice(0, 5).map((campaign, idx) => (
                      <tr key={idx} className="border-t border-border">
                        <td className="py-2 font-medium truncate max-w-[150px]">{campaign.subject}</td>
                        <td className="py-2 text-right">{campaign.sent_count}</td>
                        <td className="py-2 text-right text-green-600">
                          {campaign.sent_count > 0 ? Math.round((campaign.opened_count / campaign.sent_count) * 100) : 0}%
                        </td>
                        <td className="py-2 text-right text-blue-600">
                          {campaign.sent_count > 0 ? Math.round((campaign.replied_count / campaign.sent_count) * 100) : 0}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="text-center py-8 text-secondary">
                  <Mail className="w-12 h-12 mx-auto mb-2 opacity-50" />
                  <p>No campaigns yet</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default AdvancedReportingPage;
