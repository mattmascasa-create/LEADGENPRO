import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { TrendingUp, TrendingDown, DollarSign, Users, Target, Mail, Phone, Calendar, Download } from 'lucide-react';
import { toast } from 'react-toastify';
import DashboardLayout from '@/components/DashboardLayout';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const AnalyticsPage = () => {
  const [stats, setStats] = useState(null);
  const [timeRange, setTimeRange] = useState('30d');

  useEffect(() => {
    fetchAnalytics();
  }, [timeRange]);

  const fetchAnalytics = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/stats`);
      setStats(response.data);
    } catch (error) {
      toast.error('Failed to load analytics');
    }
  };

  const revenueData = [
    { month: 'Jan', revenue: 45000, deals: 23 },
    { month: 'Feb', revenue: 52000, deals: 28 },
    { month: 'Mar', revenue: 48000, deals: 25 },
    { month: 'Apr', revenue: 61000, deals: 32 },
    { month: 'May', revenue: 70000, deals: 38 },
    { month: 'Jun', revenue: 68000, deals: 35 }
  ];

  const conversionData = [
    { stage: 'Leads', count: 500, percentage: 100 },
    { stage: 'Contacted', count: 380, percentage: 76 },
    { stage: 'Qualified', count: 280, percentage: 56 },
    { stage: 'Proposal', count: 150, percentage: 30 },
    { stage: 'Closed', count: 95, percentage: 19 }
  ];

  const leadSourceData = [
    { name: 'Inbound', value: 45, color: 'hsl(226 71% 40%)' },
    { name: 'Cold Email', value: 30, color: 'hsl(24 95% 53%)' },
    { name: 'Referral', value: 15, color: 'hsl(142 76% 36%)' },
    { name: 'LinkedIn', value: 10, color: 'hsl(221 83% 53%)' }
  ];

  const teamPerformance = [
    { name: 'Sarah J.', leads: 85, deals: 28, revenue: 145000 },
    { name: 'Mike C.', leads: 72, deals: 24, revenue: 125000 },
    { name: 'Emma D.', leads: 68, deals: 22, revenue: 115000 },
    { name: 'John S.', leads: 55, deals: 18, revenue: 95000 }
  ];

  return (
    <DashboardLayout>
      <div>
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-4xl font-bold text-foreground mb-2">Analytics & Reports</h1>
            <p className="text-secondary">Track performance and gain insights into your sales pipeline</p>
          </div>
          <div className="flex items-center gap-3">
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
              className="px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="7d">Last 7 days</option>
              <option value="30d">Last 30 days</option>
              <option value="90d">Last 90 days</option>
              <option value="1y">Last year</option>
            </select>
            <button className="px-4 py-2 border border-border rounded-lg hover:bg-slate-50 transition-colors flex items-center gap-2">
              <Download className="w-4 h-4" />
              Export
            </button>
          </div>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {[
            {
              icon: DollarSign,
              label: 'Pipeline Value',
              value: `$${stats?.pipeline_value ? (stats.pipeline_value / 1000).toFixed(0) + 'K' : '0'}`,
              change: '+12.5%',
              trend: 'up',
              color: 'text-green-600',
              bg: 'bg-green-100'
            },
            {
              icon: Target,
              label: 'Conversion Rate',
              value: `${stats?.conversion_rate || 0}%`,
              change: '+3.2%',
              trend: 'up',
              color: 'text-primary',
              bg: 'bg-primary/10'
            },
            {
              icon: Mail,
              label: 'Email Response Rate',
              value: '34.5%',
              change: '+5.8%',
              trend: 'up',
              color: 'text-blue-600',
              bg: 'bg-blue-100'
            },
            {
              icon: Phone,
              label: 'Avg Response Time',
              value: `${stats?.avg_response_time || 0}h`,
              change: '-0.3h',
              trend: 'down',
              color: 'text-accent',
              bg: 'bg-accent/10'
            }
          ].map((metric, index) => {
            const Icon = metric.icon;
            const TrendIcon = metric.trend === 'up' ? TrendingUp : TrendingDown;
            return (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className="bg-white p-6 rounded-xl border border-border hover:shadow-md transition-all duration-200"
              >
                <div className="flex items-center justify-between mb-4">
                  <div className={`${metric.bg} ${metric.color} w-12 h-12 rounded-lg flex items-center justify-center`}>
                    <Icon className="w-6 h-6" />
                  </div>
                  <div className={`flex items-center gap-1 text-sm font-medium ${
                    metric.trend === 'up' ? 'text-green-600' : 'text-red-600'
                  }`}>
                    <TrendIcon className="w-4 h-4" />
                    {metric.change}
                  </div>
                </div>
                <p className="text-sm text-secondary mb-1">{metric.label}</p>
                <p className="text-3xl font-bold metric-value text-foreground">{metric.value}</p>
              </motion.div>
            );
          })}
        </div>

        {/* Revenue & Deals Chart */}
        <div className="bg-white p-6 rounded-xl border border-border mb-8">
          <h3 className="text-xl font-semibold text-foreground mb-6">Revenue & Deals Closed</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={revenueData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(214 32% 91%)" />
              <XAxis dataKey="month" stroke="hsl(215 16% 47%)" />
              <YAxis yAxisId="left" stroke="hsl(215 16% 47%)" />
              <YAxis yAxisId="right" orientation="right" stroke="hsl(215 16% 47%)" />
              <Tooltip
                contentStyle={{
                  background: '#ffffff',
                  border: '1px solid hsl(214 32% 91%)',
                  borderRadius: '0.5rem'
                }}
              />
              <Legend />
              <Bar yAxisId="left" dataKey="revenue" fill="hsl(226 71% 40%)" name="Revenue ($)" radius={[8, 8, 0, 0]} />
              <Bar yAxisId="right" dataKey="deals" fill="hsl(24 95% 53%)" name="Deals Closed" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Conversion Funnel & Lead Sources */}
        <div className="grid lg:grid-cols-2 gap-6 mb-8">
          {/* Conversion Funnel */}
          <div className="bg-white p-6 rounded-xl border border-border">
            <h3 className="text-xl font-semibold text-foreground mb-6">Conversion Funnel</h3>
            <div className="space-y-4">
              {conversionData.map((stage, index) => (
                <div key={index}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-foreground">{stage.stage}</span>
                    <span className="text-sm font-semibold metric-value text-primary">
                      {stage.count} ({stage.percentage}%)
                    </span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-3 overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${stage.percentage}%` }}
                      transition={{ duration: 0.8, delay: index * 0.1 }}
                      className="h-full bg-primary rounded-full"
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Lead Sources */}
          <div className="bg-white p-6 rounded-xl border border-border">
            <h3 className="text-xl font-semibold text-foreground mb-6">Lead Sources</h3>
            <div className="flex items-center justify-center">
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={leadSourceData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={2}
                    dataKey="value"
                  >
                    {leadSourceData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="grid grid-cols-2 gap-3 mt-4">
              {leadSourceData.map((source, index) => (
                <div key={index} className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: source.color }} />
                  <span className="text-sm text-secondary">{source.name}: {source.value}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Team Performance */}
        <div className="bg-white p-6 rounded-xl border border-border">
          <h3 className="text-xl font-semibold text-foreground mb-6">Team Performance</h3>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-3 px-4 text-sm font-semibold text-foreground">Team Member</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-foreground">Leads</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-foreground">Deals Closed</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-foreground">Revenue</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-foreground">Conversion</th>
                </tr>
              </thead>
              <tbody>
                {teamPerformance.map((member, index) => {
                  const conversionRate = ((member.deals / member.leads) * 100).toFixed(1);
                  return (
                    <motion.tr
                      key={index}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.1 }}
                      className="border-b border-border hover:bg-slate-50 transition-colors"
                    >
                      <td className="py-4 px-4">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 bg-gradient-to-br from-primary to-accent rounded-full flex items-center justify-center text-white font-semibold">
                            {member.name.charAt(0)}
                          </div>
                          <span className="font-medium text-foreground">{member.name}</span>
                        </div>
                      </td>
                      <td className="py-4 px-4 text-secondary">{member.leads}</td>
                      <td className="py-4 px-4 text-secondary">{member.deals}</td>
                      <td className="py-4 px-4">
                        <span className="font-semibold metric-value text-green-600">
                          ${(member.revenue / 1000).toFixed(0)}K
                        </span>
                      </td>
                      <td className="py-4 px-4">
                        <span className="inline-block px-3 py-1 bg-primary/10 text-primary rounded-full text-sm font-semibold">
                          {conversionRate}%
                        </span>
                      </td>
                    </motion.tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default AnalyticsPage;