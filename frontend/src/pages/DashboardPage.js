import React, { useEffect, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { motion } from 'framer-motion';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Users, Target, Calendar, TrendingUp, Award, LogOut, Menu } from 'lucide-react';
import { toast } from 'react-toastify';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const DashboardPage = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/stats`);
      setStats(response.data);
    } catch (error) {
      toast.error('Failed to load stats');
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
    toast.success('Logged out successfully');
  };

  const chartData = [
    { name: 'Mon', leads: 24 },
    { name: 'Tue', leads: 32 },
    { name: 'Wed', leads: 28 },
    { name: 'Thu', leads: 45 },
    { name: 'Fri', leads: 38 },
    { name: 'Sat', leads: 15 },
    { name: 'Sun', leads: 12 }
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Navigation */}
      <nav className="glassmorphism border-b border-border sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-12 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-8">
              <h1 className="text-2xl font-black text-primary">LeadGen Pro</h1>
              <div className="hidden md:flex gap-4">
                <Link to="/dashboard" className="px-4 py-2 rounded-lg bg-primary/10 text-primary font-semibold">
                  Dashboard
                </Link>
                <Link to="/leads" className="px-4 py-2 rounded-lg hover:bg-primary/10 text-foreground transition-colors">
                  Leads
                </Link>
                <Link to="/appointments" className="px-4 py-2 rounded-lg hover:bg-primary/10 text-foreground transition-colors">
                  Appointments
                </Link>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <div className="hidden md:block text-right">
                <p className="text-sm font-semibold">{user?.full_name}</p>
                <p className="text-xs text-muted-foreground capitalize">{user?.role}</p>
              </div>
              <button
                onClick={handleLogout}
                className="p-2 rounded-lg hover:bg-destructive/10 text-destructive transition-colors"
              >
                <LogOut className="w-5 h-5" />
              </button>
              <button
                onClick={() => setMenuOpen(!menuOpen)}
                className="md:hidden p-2 rounded-lg hover:bg-primary/10"
              >
                <Menu className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Mobile Menu */}
          {menuOpen && (
            <div className="md:hidden mt-4 space-y-2">
              <Link to="/dashboard" className="block px-4 py-2 rounded-lg bg-primary/10 text-primary font-semibold">
                Dashboard
              </Link>
              <Link to="/leads" className="block px-4 py-2 rounded-lg hover:bg-primary/10 text-foreground">
                Leads
              </Link>
              <Link to="/appointments" className="block px-4 py-2 rounded-lg hover:bg-primary/10 text-foreground">
                Appointments
              </Link>
            </div>
          )}
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-12 py-8">
        {/* Welcome Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h2 className="text-4xl font-black mb-2">Welcome back, {user?.full_name}! 🚀</h2>
          <p className="text-muted-foreground text-lg">Here's what's happening with your leads today</p>
        </motion.div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {[
            {
              icon: <Target className="w-8 h-8" />,
              label: 'Total Leads',
              value: stats?.total_leads || 0,
              color: 'text-primary',
              bg: 'bg-primary/10'
            },
            {
              icon: <Users className="w-8 h-8" />,
              label: 'Team Members',
              value: stats?.total_users || 0,
              color: 'text-accent',
              bg: 'bg-accent/10'
            },
            {
              icon: <Calendar className="w-8 h-8" />,
              label: 'Appointments',
              value: stats?.total_appointments || 0,
              color: 'text-green-500',
              bg: 'bg-green-500/10'
            },
            {
              icon: <TrendingUp className="w-8 h-8" />,
              label: 'Conversion Rate',
              value: `${stats?.conversion_rate || 0}%`,
              color: 'text-yellow-500',
              bg: 'bg-yellow-500/10'
            }
          ].map((stat, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className="glassmorphism p-6 rounded-xl hover:border-primary transition-all group"
            >
              <div className={`${stat.bg} ${stat.color} w-16 h-16 rounded-lg flex items-center justify-center mb-4 group-hover:scale-110 transition-transform`}>
                {stat.icon}
              </div>
              <p className="text-muted-foreground text-sm mb-1">{stat.label}</p>
              <p className="metric-value text-3xl font-bold">{stat.value}</p>
            </motion.div>
          ))}
        </div>

        {/* Chart Section */}
        <div className="grid lg:grid-cols-2 gap-6 mb-8">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="glassmorphism p-6 rounded-xl"
          >
            <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
              <BarChart className="w-6 h-6 text-primary" />
              Weekly Lead Activity
            </h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(240 3.7% 15.9%)" />
                <XAxis dataKey="name" stroke="hsl(0 0% 98%)" />
                <YAxis stroke="hsl(0 0% 98%)" />
                <Tooltip
                  contentStyle={{
                    background: 'hsl(240 10% 3.9%)',
                    border: '1px solid hsl(240 3.7% 15.9%)',
                    borderRadius: '0.5rem'
                  }}
                />
                <Bar dataKey="leads" fill="hsl(263.4 70% 50.4%)" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="glassmorphism p-6 rounded-xl"
          >
            <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
              <Award className="w-6 h-6 text-accent" />
              Top Performers
            </h3>
            <div className="space-y-4">
              {[
                { name: 'Sarah Johnson', leads: 45, badge: '🥇' },
                { name: 'Mike Chen', leads: 38, badge: '🥈' },
                { name: 'Emma Davis', leads: 32, badge: '🥉' }
              ].map((performer, index) => (
                <div key={index} className="flex items-center justify-between p-4 bg-secondary rounded-lg">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{performer.badge}</span>
                    <div>
                      <p className="font-semibold">{performer.name}</p>
                      <p className="text-sm text-muted-foreground">{performer.leads} leads closed</p>
                    </div>
                  </div>
                  <div className="px-4 py-2 bg-primary/10 text-primary rounded-lg font-bold">
                    +{performer.leads}
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        </div>

        {/* Quick Actions */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glassmorphism p-6 rounded-xl"
        >
          <h3 className="text-xl font-bold mb-6">Quick Actions</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Link to="/leads">
              <button className="w-full p-4 bg-primary text-primary-foreground rounded-lg font-semibold hover:scale-105 transition-transform">
                Add New Lead
              </button>
            </Link>
            <Link to="/appointments">
              <button className="w-full p-4 bg-accent text-accent-foreground rounded-lg font-semibold hover:scale-105 transition-transform">
                Schedule Meeting
              </button>
            </Link>
            <button className="w-full p-4 border-2 border-primary text-primary rounded-lg font-semibold hover:bg-primary/10 transition-colors">
              View Reports
            </button>
            <button className="w-full p-4 border-2 border-accent text-accent rounded-lg font-semibold hover:bg-accent/10 transition-colors">
              Team Chat
            </button>
          </div>
        </motion.div>
      </main>
    </div>
  );
};

export default DashboardPage;