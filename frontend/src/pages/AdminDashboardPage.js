import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  PieChart, Pie, Cell, LineChart, Line 
} from 'recharts';
import { 
  Users, Target, Phone, Calendar, TrendingUp, Award, Clock,
  ChevronRight, Plus, Send, Sparkles, Activity, UserCheck
} from 'lucide-react';
import { toast } from 'react-toastify';
import { useNavigate } from 'react-router-dom';
import DashboardLayout from '@/components/DashboardLayout';
import NotificationStatsWidget from '@/components/NotificationStatsWidget';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const AdminDashboardPage = () => {
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [employeePerformance, setEmployeePerformance] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showGoalsModal, setShowGoalsModal] = useState(null);
  const [goalForm, setGoalForm] = useState({
    calls_target: 20,
    meetings_target: 3,
    emails_target: 10,
    notes: ''
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [statsRes, perfRes] = await Promise.all([
        axios.get(`${API_URL}/api/admin/dashboard/stats`),
        axios.get(`${API_URL}/api/admin/employees/performance`)
      ]);
      setStats(statsRes.data);
      setEmployeePerformance(perfRes.data);
    } catch (error) {
      toast.error('Failed to load admin dashboard data');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleSetGoals = async (employeeId) => {
    try {
      const today = new Date().toISOString().split('T')[0];
      await axios.post(`${API_URL}/api/admin/daily-goals`, {
        employee_id: employeeId,
        date: today,
        ...goalForm
      });
      toast.success('Daily goals set successfully!');
      setShowGoalsModal(null);
      setGoalForm({ calls_target: 20, meetings_target: 3, emails_target: 10, notes: '' });
    } catch (error) {
      toast.error('Failed to set goals');
    }
  };

  const handleDistributeRoundRobin = async () => {
    try {
      const response = await axios.post(`${API_URL}/api/admin/distribute-leads-roundrobin`);
      toast.success(`${response.data.total_distributed} leads distributed!`);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to distribute leads');
    }
  };

  const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6'];

  const pipelineData = stats ? [
    { name: 'Prospecting', value: stats.pipeline_stages?.prospecting || 0 },
    { name: 'Qualified', value: stats.pipeline_stages?.qualified || 0 },
    { name: 'Proposal', value: stats.pipeline_stages?.proposal || 0 },
    { name: 'Negotiation', value: stats.pipeline_stages?.negotiation || 0 },
    { name: 'Closed', value: stats.pipeline_stages?.closed || 0 }
  ] : [];

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <div className="text-primary text-xl">Loading admin dashboard...</div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div data-testid="admin-dashboard-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6 lg:mb-8">
          <div>
            <h1 className="text-2xl lg:text-4xl font-bold text-foreground mb-1 lg:mb-2">Admin Dashboard</h1>
            <p className="text-sm lg:text-base text-secondary">Company-wide overview and employee performance</p>
          </div>
          <div className="flex flex-wrap gap-2 lg:gap-3">
            <button
              onClick={handleDistributeRoundRobin}
              className="px-3 lg:px-4 py-2 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 flex items-center gap-2 text-sm lg:text-base"
            >
              <Send className="w-4 h-4" />
              <span className="hidden sm:inline">Auto-</span>Distribute
            </button>
            <button
              onClick={() => navigate('/admin/users')}
              className="px-3 lg:px-4 py-2 bg-primary text-white rounded-lg font-medium hover:bg-primary/90 flex items-center gap-2 text-sm lg:text-base"
            >
              <Plus className="w-4 h-4" />
              <span className="hidden sm:inline">Add</span> Employee
            </button>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 lg:gap-6 mb-6 lg:mb-8">
          {[
            { icon: Users, label: 'Employees', value: stats?.total_employees || 0, color: 'text-blue-600', bg: 'bg-blue-100' },
            { icon: Target, label: 'Active Leads', value: stats?.active_leads || 0, color: 'text-green-600', bg: 'bg-green-100' },
            { icon: Phone, label: 'Calls Today', value: stats?.calls_today || 0, color: 'text-orange-600', bg: 'bg-orange-100' },
            { icon: Calendar, label: 'Meetings', value: stats?.meetings_today || 0, color: 'text-purple-600', bg: 'bg-purple-100' }
          ].map((stat, index) => {
            const Icon = stat.icon;
            return (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className="bg-white p-4 lg:p-6 rounded-xl border border-border hover:shadow-md transition-all"
              >
                <div className={`${stat.bg} ${stat.color} w-10 h-10 lg:w-12 lg:h-12 rounded-lg flex items-center justify-center mb-3 lg:mb-4`}>
                  <Icon className="w-5 h-5 lg:w-6 lg:h-6" />
                </div>
                <p className="text-xs lg:text-sm text-secondary mb-1">{stat.label}</p>
                <p className="text-2xl lg:text-3xl font-bold text-foreground">{stat.value}</p>
              </motion.div>
            );
          })}
        </div>

        {/* Charts Row */}
        <div className="grid lg:grid-cols-2 gap-6 mb-8">
          {/* Pipeline Overview */}
          <div className="bg-white p-6 rounded-xl border border-border">
            <h3 className="text-lg font-semibold text-foreground mb-6 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-primary" />
              Pipeline Overview
            </h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={pipelineData}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(214 32% 91%)" />
                <XAxis dataKey="name" stroke="hsl(215 16% 47%)" fontSize={12} />
                <YAxis stroke="hsl(215 16% 47%)" />
                <Tooltip
                  contentStyle={{
                    background: '#ffffff',
                    border: '1px solid hsl(214 32% 91%)',
                    borderRadius: '0.5rem'
                  }}
                />
                <Bar dataKey="value" fill="hsl(226 71% 40%)" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Conversion Rate */}
          <div className="bg-white p-6 rounded-xl border border-border">
            <h3 className="text-lg font-semibold text-foreground mb-6 flex items-center gap-2">
              <Award className="w-5 h-5 text-green-600" />
              Conversion Stats
            </h3>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-5xl font-bold text-foreground mb-2">{stats?.conversion_rate || 0}%</p>
                <p className="text-secondary">Overall Conversion Rate</p>
              </div>
              <ResponsiveContainer width={150} height={150}>
                <PieChart>
                  <Pie
                    data={pipelineData}
                    cx="50%"
                    cy="50%"
                    innerRadius={40}
                    outerRadius={60}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {pipelineData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="grid grid-cols-3 gap-4 mt-6 pt-6 border-t border-border">
              <div>
                <p className="text-2xl font-bold text-foreground">{stats?.total_leads || 0}</p>
                <p className="text-sm text-secondary">Total Leads</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-foreground">{stats?.total_calls || 0}</p>
                <p className="text-sm text-secondary">Total Calls</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-foreground">{stats?.total_meetings || 0}</p>
                <p className="text-sm text-secondary">Total Meetings</p>
              </div>
            </div>
          </div>
        </div>

        {/* Smart Alerts Widget */}
        <div className="grid lg:grid-cols-3 gap-6 mb-8">
          <div className="lg:col-span-2 bg-white p-6 rounded-xl border border-border">
            <h3 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
              <Activity className="w-5 h-5 text-primary" />
              Quick Actions
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <button
                onClick={() => navigate('/leads')}
                className="p-4 bg-slate-50 rounded-xl hover:bg-slate-100 transition-colors text-center"
              >
                <Target className="w-8 h-8 text-primary mx-auto mb-2" />
                <p className="text-sm font-medium">View Leads</p>
              </button>
              <button
                onClick={() => navigate('/calendar')}
                className="p-4 bg-slate-50 rounded-xl hover:bg-slate-100 transition-colors text-center"
              >
                <Calendar className="w-8 h-8 text-purple-500 mx-auto mb-2" />
                <p className="text-sm font-medium">Calendar</p>
              </button>
              <button
                onClick={() => navigate('/calls')}
                className="p-4 bg-slate-50 rounded-xl hover:bg-slate-100 transition-colors text-center"
              >
                <Phone className="w-8 h-8 text-green-500 mx-auto mb-2" />
                <p className="text-sm font-medium">Call Logs</p>
              </button>
              <button
                onClick={() => navigate('/team-chat')}
                className="p-4 bg-slate-50 rounded-xl hover:bg-slate-100 transition-colors text-center"
              >
                <Send className="w-8 h-8 text-blue-500 mx-auto mb-2" />
                <p className="text-sm font-medium">Team Chat</p>
              </button>
            </div>
          </div>
          <div className="lg:col-span-1">
            <NotificationStatsWidget />
          </div>
        </div>

        {/* Employee Performance Table */}
        <div className="bg-white rounded-xl border border-border overflow-hidden">
          <div className="p-4 lg:p-6 border-b border-border flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <h3 className="text-base lg:text-lg font-semibold text-foreground flex items-center gap-2">
              <UserCheck className="w-5 h-5 text-primary" />
              Employee Performance
            </h3>
            <button
              onClick={() => navigate('/admin/distribute')}
              className="text-sm text-primary hover:underline flex items-center gap-1"
            >
              Manage Distribution
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
          
          {/* Scrollable table wrapper for mobile */}
          <div className="overflow-x-auto">
            <table className="w-full min-w-[600px]">
              <thead className="bg-slate-50 border-b border-border">
                <tr>
                  <th className="text-left px-4 lg:px-6 py-3 lg:py-4 text-xs lg:text-sm font-semibold text-secondary">Employee</th>
                  <th className="text-center px-3 lg:px-6 py-3 lg:py-4 text-xs lg:text-sm font-semibold text-secondary">Today</th>
                  <th className="text-center px-3 lg:px-6 py-3 lg:py-4 text-xs lg:text-sm font-semibold text-secondary">Total</th>
                  <th className="text-center px-3 lg:px-6 py-3 lg:py-4 text-xs lg:text-sm font-semibold text-secondary">Meetings</th>
                  <th className="text-center px-3 lg:px-6 py-3 lg:py-4 text-xs lg:text-sm font-semibold text-secondary">Leads</th>
                  <th className="text-center px-3 lg:px-6 py-3 lg:py-4 text-xs lg:text-sm font-semibold text-secondary">Conv%</th>
                  <th className="text-right px-4 lg:px-6 py-3 lg:py-4 text-xs lg:text-sm font-semibold text-secondary">Actions</th>
                </tr>
              </thead>
              <tbody>
                {employeePerformance.map((emp, index) => (
                  <tr key={emp.employee_id} className="border-b border-border hover:bg-slate-50 transition-colors">
                    <td className="px-4 lg:px-6 py-3 lg:py-4">
                      <div className="flex items-center gap-2 lg:gap-3">
                        <div className="w-8 h-8 lg:w-10 lg:h-10 bg-gradient-to-br from-primary to-accent rounded-full flex items-center justify-center text-white font-semibold text-sm lg:text-base flex-shrink-0">
                          {emp.employee_name?.charAt(0) || 'U'}
                        </div>
                        <div className="min-w-0">
                          <p className="font-medium text-foreground text-sm lg:text-base truncate">{emp.employee_name}</p>
                          <p className="text-xs lg:text-sm text-secondary truncate">{emp.department || emp.role}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-3 lg:px-6 py-3 lg:py-4 text-center">
                      <span className={`text-base lg:text-lg font-semibold ${emp.calls_today >= 10 ? 'text-green-600' : emp.calls_today >= 5 ? 'text-orange-600' : 'text-red-600'}`}>
                        {emp.calls_today}
                      </span>
                    </td>
                    <td className="px-3 lg:px-6 py-3 lg:py-4 text-center text-foreground text-sm lg:text-base">{emp.calls_total}</td>
                    <td className="px-3 lg:px-6 py-3 lg:py-4 text-center text-foreground text-sm lg:text-base">{emp.meetings_today}</td>
                    <td className="px-3 lg:px-6 py-3 lg:py-4 text-center text-foreground text-sm lg:text-base">{emp.leads_assigned}</td>
                    <td className="px-3 lg:px-6 py-3 lg:py-4 text-center">
                      <span className={`px-2 py-1 rounded-full text-xs lg:text-sm font-medium ${
                        emp.conversion_rate >= 20 ? 'bg-green-100 text-green-700' : 
                        emp.conversion_rate >= 10 ? 'bg-orange-100 text-orange-700' : 
                        'bg-slate-100 text-slate-700'
                      }`}>
                        {emp.conversion_rate}%
                      </span>
                    </td>
                    <td className="px-4 lg:px-6 py-3 lg:py-4 text-right">
                      <button
                        onClick={() => setShowGoalsModal(emp)}
                        className="px-2 lg:px-3 py-1 lg:py-1.5 bg-primary/10 text-primary rounded-lg text-xs lg:text-sm font-medium hover:bg-primary/20 transition-colors"
                      >
                        Goals
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {employeePerformance.length === 0 && (
            <div className="text-center py-8 lg:py-12">
              <Users className="w-10 h-10 lg:w-12 lg:h-12 text-secondary mx-auto mb-4" />
              <p className="text-secondary text-sm lg:text-base">No employees found</p>
              <button
                onClick={() => navigate('/admin/users')}
                className="mt-4 px-4 py-2 bg-primary text-white rounded-lg font-medium hover:bg-primary/90 text-sm lg:text-base"
              >
                Add Your First Employee
              </button>
            </div>
          )}
        </div>

        {/* Set Goals Modal */}
        {showGoalsModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="bg-white rounded-xl shadow-2xl w-full max-w-md mx-4"
            >
              <div className="p-6 border-b border-border">
                <h3 className="text-xl font-bold">Set Daily Goals for {showGoalsModal.employee_name}</h3>
              </div>
              <div className="p-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Calls Target</label>
                  <input
                    type="number"
                    value={goalForm.calls_target}
                    onChange={(e) => setGoalForm({...goalForm, calls_target: parseInt(e.target.value) || 0})}
                    className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Meetings Target</label>
                  <input
                    type="number"
                    value={goalForm.meetings_target}
                    onChange={(e) => setGoalForm({...goalForm, meetings_target: parseInt(e.target.value) || 0})}
                    className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Emails Target</label>
                  <input
                    type="number"
                    value={goalForm.emails_target}
                    onChange={(e) => setGoalForm({...goalForm, emails_target: parseInt(e.target.value) || 0})}
                    className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Notes for Employee</label>
                  <textarea
                    value={goalForm.notes}
                    onChange={(e) => setGoalForm({...goalForm, notes: e.target.value})}
                    placeholder="Add notes or instructions for the employee..."
                    rows={3}
                    className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary resize-none"
                  />
                </div>
              </div>
              <div className="p-6 border-t border-border flex gap-3">
                <button
                  onClick={() => setShowGoalsModal(null)}
                  className="flex-1 py-2 border border-border rounded-lg font-medium hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleSetGoals(showGoalsModal.employee_id)}
                  className="flex-1 py-2 bg-primary text-white rounded-lg font-medium hover:bg-primary/90"
                >
                  Set Goals
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
};

export default AdminDashboardPage;
