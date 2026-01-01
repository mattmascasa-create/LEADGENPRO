import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts';
import { TrendingUp, Users, Target, Calendar, Sparkles, ArrowRight, Activity } from 'lucide-react';
import { toast } from 'react-toastify';
import DashboardLayout from '@/components/DashboardLayout';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const DashboardPage = () => {
  const [stats, setStats] = useState(null);
  const [insights, setInsights] = useState([]);
  const [activities, setActivities] = useState([]);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [statsRes, insightsRes, activitiesRes] = await Promise.all([
        axios.get(`${API_URL}/api/stats`),
        axios.get(`${API_URL}/api/insights`),
        axios.get(`${API_URL}/api/activities?limit=10`)
      ]);
      setStats(statsRes.data);
      setInsights(insightsRes.data);
      setActivities(activitiesRes.data);
    } catch (error) {
      toast.error('Failed to load dashboard data');
    }
  };

  const chartData = [
    { name: 'Mon', leads: 24, deals: 12 },
    { name: 'Tue', leads: 32, deals: 18 },
    { name: 'Wed', leads: 28, deals: 15 },
    { name: 'Thu', leads: 45, deals: 22 },
    { name: 'Fri', leads: 38, deals: 20 },
    { name: 'Sat', leads: 15, deals: 8 },
    { name: 'Sun', leads: 12, deals: 6 }
  ];

  return (
    <DashboardLayout>
      <div>
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-foreground mb-2">Dashboard</h1>
          <p className="text-secondary">Welcome back! Here's what's happening today.</p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {[
            { icon: Target, label: 'Total Leads', value: stats?.total_leads || 0, color: 'text-primary', bg: 'bg-primary/10' },
            { icon: Users, label: 'Team Members', value: stats?.total_users || 0, color: 'text-accent', bg: 'bg-accent/10' },
            { icon: Calendar, label: 'Appointments', value: stats?.total_appointments || 0, color: 'text-green-600', bg: 'bg-green-100' },
            { icon: TrendingUp, label: 'Conversion Rate', value: `${stats?.conversion_rate || 0}%`, color: 'text-blue-600', bg: 'bg-blue-100' }
          ].map((stat, index) => {
            const Icon = stat.icon;
            return (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className="bg-white p-6 rounded-xl border border-border hover:border-primary transition-all duration-200 hover:shadow-md"
              >
                <div className={`${stat.bg} ${stat.color} w-12 h-12 rounded-lg flex items-center justify-center mb-4`}>
                  <Icon className="w-6 h-6" />
                </div>
                <p className="text-sm text-secondary mb-1">{stat.label}</p>
                <p className="text-3xl font-bold metric-value text-foreground">{stat.value}</p>
              </motion.div>
            );
          })}
        </div>

        {/* AI Insights */}
        {insights.length > 0 && (
          <div className="mb-8">
            <h2 className="text-2xl font-semibold text-foreground mb-4 flex items-center gap-2">
              <Sparkles className="w-6 h-6 text-accent" />
              AI Insights
            </h2>
            <div className="grid md:grid-cols-2 gap-4">
              {insights.map((insight, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className="ai-card p-6 rounded-xl"
                >
                  <div className="flex items-start gap-4">
                    <div className="w-10 h-10 bg-accent/10 rounded-lg flex items-center justify-center flex-shrink-0">
                      <Sparkles className="w-5 h-5 text-accent" />
                    </div>
                    <div className="flex-1">
                      <h3 className="font-semibold text-foreground mb-2">{insight.message}</h3>
                      {insight.action_items && insight.action_items.length > 0 && (
                        <ul className="space-y-1">
                          {insight.action_items.map((item, i) => (
                            <li key={i} className="text-sm text-secondary flex items-center gap-2">
                              <ArrowRight className="w-3 h-3" />
                              {item}
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        )}

        {/* Charts */}
        <div className="grid lg:grid-cols-2 gap-6 mb-8">
          <div className="bg-white p-6 rounded-xl border border-border">
            <h3 className="text-lg font-semibold text-foreground mb-6">Weekly Activity</h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(214 32% 91%)" />
                <XAxis dataKey="name" stroke="hsl(215 16% 47%)" />
                <YAxis stroke="hsl(215 16% 47%)" />
                <Tooltip
                  contentStyle={{
                    background: '#ffffff',
                    border: '1px solid hsl(214 32% 91%)',
                    borderRadius: '0.5rem'
                  }}
                />
                <Bar dataKey="leads" fill="hsl(226 71% 40%)" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-white p-6 rounded-xl border border-border">
            <h3 className="text-lg font-semibold text-foreground mb-6">Conversion Trend</h3>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(214 32% 91%)" />
                <XAxis dataKey="name" stroke="hsl(215 16% 47%)" />
                <YAxis stroke="hsl(215 16% 47%)" />
                <Tooltip
                  contentStyle={{
                    background: '#ffffff',
                    border: '1px solid hsl(214 32% 91%)',
                    borderRadius: '0.5rem'
                  }}
                />
                <Line type="monotone" dataKey="deals" stroke="hsl(24 95% 53%)" strokeWidth={3} dot={{ fill: 'hsl(24 95% 53%)' }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Activity Feed */}
        <div className="bg-white p-6 rounded-xl border border-border">
          <h3 className="text-lg font-semibold text-foreground mb-6 flex items-center gap-2">
            <Activity className="w-5 h-5" />
            Recent Activity
          </h3>
          <div className="space-y-4">
            {activities.length > 0 ? activities.map((activity, index) => (
              <div key={index} className="flex items-start gap-4 pb-4 border-b border-border last:border-0">
                <div className="w-2 h-2 bg-primary rounded-full mt-2" />
                <div className="flex-1">
                  <p className="text-sm text-foreground">{activity.description}</p>
                  <p className="text-xs text-secondary mt-1">
                    {new Date(activity.created_at).toLocaleString()}
                  </p>
                </div>
              </div>
            )) : (
              <p className="text-sm text-secondary text-center py-8">No recent activity</p>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default DashboardPage;