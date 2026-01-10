import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer 
} from 'recharts';
import { 
  Phone, Calendar, Target, TrendingUp, Clock, CheckCircle2, 
  AlertCircle, PhoneCall, Users, ArrowRight, Sparkles, MessageSquare
} from 'lucide-react';
import { toast } from 'react-toastify';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import DashboardLayout from '@/components/DashboardLayout';
import NotificationStatsWidget from '@/components/NotificationStatsWidget';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const EmployeeDashboardPage = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [dashboard, setDashboard] = useState(null);
  const [myLeads, setMyLeads] = useState([]);
  const [myTasks, setMyTasks] = useState([]);
  const [weeklyStats, setWeeklyStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [dashboardRes, leadsRes, tasksRes, statsRes] = await Promise.all([
        axios.get(`${API_URL}/api/employee/dashboard`),
        axios.get(`${API_URL}/api/employee/my-leads?limit=10`),
        axios.get(`${API_URL}/api/employee/my-tasks?completed=false`),
        axios.get(`${API_URL}/api/employee/my-stats`)
      ]);
      setDashboard(dashboardRes.data);
      setMyLeads(leadsRes.data);
      setMyTasks(tasksRes.data);
      setWeeklyStats(statsRes.data);
    } catch (error) {
      toast.error('Failed to load dashboard data');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const getProgressColor = (current, target) => {
    const percentage = (current / target) * 100;
    if (percentage >= 100) return 'bg-green-500';
    if (percentage >= 50) return 'bg-orange-500';
    return 'bg-red-500';
  };

  const getProgressPercentage = (current, target) => {
    return Math.min((current / target) * 100, 100);
  };

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <div className="text-primary text-xl">Loading your dashboard...</div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div data-testid="employee-dashboard-page">
        {/* Header */}
        <div className="mb-6 lg:mb-8">
          <h1 className="text-2xl lg:text-4xl font-bold text-foreground mb-1 lg:mb-2">
            Welcome back, {user?.full_name?.split(' ')[0]}! 👋
          </h1>
          <p className="text-sm lg:text-base text-secondary">Here&apos;s your daily overview and goals</p>
        </div>

        {/* Admin Notes (if any) */}
        {dashboard?.admin_notes && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-4 lg:p-6 mb-6 lg:mb-8"
          >
            <div className="flex items-start gap-3 lg:gap-4">
              <div className="w-8 h-8 lg:w-10 lg:h-10 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
                <MessageSquare className="w-4 h-4 lg:w-5 lg:h-5 text-blue-600" />
              </div>
              <div>
                <h3 className="font-semibold text-blue-900 mb-1 text-sm lg:text-base">📝 Note from Admin</h3>
                <p className="text-blue-800 text-sm lg:text-base">{dashboard.admin_notes}</p>
              </div>
            </div>
          </motion.div>
        )}

        {/* Daily Goals Progress */}
        <div className="bg-white rounded-xl border border-border p-4 lg:p-6 mb-6 lg:mb-8">
          <h2 className="text-lg lg:text-xl font-semibold text-foreground mb-4 lg:mb-6 flex items-center gap-2">
            <Target className="w-4 h-4 lg:w-5 lg:h-5 text-primary" />
            Today&apos;s Goals
          </h2>
          <div className="grid gap-4 lg:gap-6">
            {/* Calls Progress */}
            <div className="p-3 lg:p-4 bg-slate-50 rounded-lg">
              <div className="flex items-center justify-between mb-2 lg:mb-3">
                <div className="flex items-center gap-2">
                  <Phone className="w-4 h-4 lg:w-5 lg:h-5 text-blue-600" />
                  <span className="font-medium text-sm lg:text-base">Calls Made</span>
                </div>
                <span className="text-base lg:text-lg font-bold">
                  {dashboard?.progress?.calls_made || 0} / {dashboard?.progress?.calls_target || 20}
                </span>
              </div>
              <div className="w-full bg-slate-200 rounded-full h-2 lg:h-3">
                <div 
                  className={`h-2 lg:h-3 rounded-full transition-all duration-500 ${getProgressColor(dashboard?.progress?.calls_made || 0, dashboard?.progress?.calls_target || 20)}`}
                  style={{ width: `${getProgressPercentage(dashboard?.progress?.calls_made || 0, dashboard?.progress?.calls_target || 20)}%` }}
                />
              </div>
              {(dashboard?.progress?.calls_made || 0) >= (dashboard?.progress?.calls_target || 20) && (
                <div className="flex items-center gap-1 mt-2 text-green-600 text-xs lg:text-sm">
                  <CheckCircle2 className="w-3 h-3 lg:w-4 lg:h-4" />
                  Goal achieved! 🎉
                </div>
              )}
            </div>

            {/* Meetings Progress */}
            <div className="p-3 lg:p-4 bg-slate-50 rounded-lg">
              <div className="flex items-center justify-between mb-2 lg:mb-3">
                <div className="flex items-center gap-2">
                  <Calendar className="w-4 h-4 lg:w-5 lg:h-5 text-purple-600" />
                  <span className="font-medium text-sm lg:text-base">Meetings Scheduled</span>
                </div>
                <span className="text-base lg:text-lg font-bold">
                  {dashboard?.progress?.meetings_scheduled || 0} / {dashboard?.progress?.meetings_target || 3}
                </span>
              </div>
              <div className="w-full bg-slate-200 rounded-full h-2 lg:h-3">
                <div 
                  className={`h-2 lg:h-3 rounded-full transition-all duration-500 ${getProgressColor(dashboard?.progress?.meetings_scheduled || 0, dashboard?.progress?.meetings_target || 3)}`}
                  style={{ width: `${getProgressPercentage(dashboard?.progress?.meetings_scheduled || 0, dashboard?.progress?.meetings_target || 3)}%` }}
                />
              </div>
              {(dashboard?.progress?.meetings_scheduled || 0) >= (dashboard?.progress?.meetings_target || 3) && (
                <div className="flex items-center gap-1 mt-2 text-green-600 text-xs lg:text-sm">
                  <CheckCircle2 className="w-3 h-3 lg:w-4 lg:h-4" />
                  Goal achieved! 🎉
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Stats and Chart Row */}
        <div className="grid gap-4 lg:gap-6 mb-6 lg:mb-8">
          {/* Personal Stats */}
          <div className="grid grid-cols-2 gap-3 lg:gap-4">
            {[
              { icon: Users, label: 'My Leads', value: dashboard?.my_leads_count || 0, color: 'text-blue-600', bg: 'bg-blue-100' },
              { icon: CheckCircle2, label: 'Pending Tasks', value: dashboard?.pending_tasks_count || 0, color: 'text-orange-600', bg: 'bg-orange-100' },
              { icon: TrendingUp, label: 'Conversion Rate', value: `${dashboard?.personal_stats?.conversion_rate || 0}%`, color: 'text-green-600', bg: 'bg-green-100' },
              { icon: Phone, label: 'Total Calls', value: dashboard?.personal_stats?.total_calls || 0, color: 'text-purple-600', bg: 'bg-purple-100' }
            ].map((stat, index) => {
              const Icon = stat.icon;
              return (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: index * 0.1 }}
                  className="bg-white p-3 lg:p-4 rounded-xl border border-border"
                >
                  <div className={`${stat.bg} ${stat.color} w-8 h-8 lg:w-10 lg:h-10 rounded-lg flex items-center justify-center mb-2 lg:mb-3`}>
                    <Icon className="w-4 h-4 lg:w-5 lg:h-5" />
                  </div>
                  <p className="text-xs text-secondary mb-1">{stat.label}</p>
                  <p className="text-xl lg:text-2xl font-bold text-foreground">{stat.value}</p>
                </motion.div>
              );
            })}
          </div>

          {/* Weekly Activity Chart */}
          <div className="bg-white rounded-xl border border-border p-4 lg:p-6">
            <h3 className="text-base lg:text-lg font-semibold text-foreground mb-4 lg:mb-6 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 lg:w-5 lg:h-5 text-primary" />
              Your Weekly Activity
            </h3>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={weeklyStats?.daily_calls || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(214 32% 91%)" />
                <XAxis dataKey="day" stroke="hsl(215 16% 47%)" fontSize={11} />
                <YAxis stroke="hsl(215 16% 47%)" fontSize={11} />
                <Tooltip
                  contentStyle={{
                    background: '#ffffff',
                    border: '1px solid hsl(214 32% 91%)',
                    borderRadius: '0.5rem',
                    fontSize: '12px'
                  }}
                />
                <Bar dataKey="calls" fill="hsl(226 71% 40%)" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Leads and Tasks Row */}
        <div className="grid gap-4 lg:gap-6 lg:grid-cols-2">
          {/* My Leads to Call */}
          <div className="bg-white rounded-xl border border-border overflow-hidden">
            <div className="p-4 lg:p-6 border-b border-border flex items-center justify-between">
              <h3 className="text-base lg:text-lg font-semibold text-foreground flex items-center gap-2">
                <PhoneCall className="w-4 h-4 lg:w-5 lg:h-5 text-green-600" />
                Leads to Call
              </h3>
              <button
                onClick={() => navigate('/call-lists')}
                className="text-xs lg:text-sm text-primary hover:underline flex items-center gap-1"
              >
                View All
                <ArrowRight className="w-3 h-3 lg:w-4 lg:h-4" />
              </button>
            </div>
            <div className="divide-y divide-border max-h-64 lg:max-h-80 overflow-y-auto">
              {myLeads.length > 0 ? myLeads.slice(0, 5).map((lead) => (
                <div
                  key={lead.id}
                  className="p-3 lg:p-4 hover:bg-slate-50 transition-colors cursor-pointer flex items-center justify-between"
                  onClick={() => navigate(`/leads/${lead.id}`)}
                >
                  <div className="flex items-center gap-2 lg:gap-3 min-w-0">
                    <div className="w-8 h-8 lg:w-10 lg:h-10 bg-gradient-to-br from-green-400 to-green-600 rounded-full flex items-center justify-center text-white font-semibold text-sm flex-shrink-0">
                      {lead.first_name?.charAt(0) || 'L'}
                    </div>
                    <div className="min-w-0">
                      <p className="font-medium text-foreground text-sm lg:text-base truncate">{lead.first_name} {lead.last_name}</p>
                      <p className="text-xs lg:text-sm text-secondary truncate">{lead.company}</p>
                    </div>
                  </div>
                  <span className={`px-2 py-0.5 lg:py-1 rounded-full text-xs font-medium flex-shrink-0 ${
                    lead.status === 'new' ? 'bg-blue-100 text-blue-700' :
                    lead.status === 'contacted' ? 'bg-green-100 text-green-700' :
                    'bg-orange-100 text-orange-700'
                  }`}>
                    {lead.status}
                  </span>
                </div>
              )) : (
                <div className="p-6 lg:p-8 text-center text-secondary">
                  <Users className="w-10 h-10 lg:w-12 lg:h-12 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No leads assigned yet</p>
                </div>
              )}
            </div>
          </div>

          {/* My Tasks */}
          <div className="bg-white rounded-xl border border-border overflow-hidden">
            <div className="p-4 lg:p-6 border-b border-border flex items-center justify-between">
              <h3 className="text-base lg:text-lg font-semibold text-foreground flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 lg:w-5 lg:h-5 text-orange-600" />
                Pending Tasks
              </h3>
              <button
                onClick={() => navigate('/tasks')}
                className="text-xs lg:text-sm text-primary hover:underline flex items-center gap-1"
              >
                View All
                <ArrowRight className="w-3 h-3 lg:w-4 lg:h-4" />
              </button>
            </div>
            <div className="divide-y divide-border max-h-64 lg:max-h-80 overflow-y-auto">
              {myTasks.length > 0 ? myTasks.slice(0, 5).map((task) => (
                <div
                  key={task.id}
                  className="p-3 lg:p-4 hover:bg-slate-50 transition-colors"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="font-medium text-foreground text-sm lg:text-base truncate">{task.title}</p>
                      <p className="text-xs lg:text-sm text-secondary mt-1 line-clamp-1">{task.description || 'No description'}</p>
                    </div>
                    <span className={`px-2 py-0.5 lg:py-1 rounded-full text-xs font-medium flex-shrink-0 ${
                      task.priority === 'high' ? 'bg-red-100 text-red-700' :
                      task.priority === 'medium' ? 'bg-orange-100 text-orange-700' :
                      'bg-slate-100 text-slate-700'
                    }`}>
                      {task.priority}
                    </span>
                  </div>
                  {task.due_date && (
                    <div className="flex items-center gap-1 mt-2 text-xs lg:text-sm text-secondary">
                      <Clock className="w-3 h-3" />
                      Due: {new Date(task.due_date).toLocaleDateString()}
                    </div>
                  )}
                </div>
              )) : (
                <div className="p-6 lg:p-8 text-center text-secondary">
                  <CheckCircle2 className="w-10 h-10 lg:w-12 lg:h-12 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No pending tasks</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default EmployeeDashboardPage;
