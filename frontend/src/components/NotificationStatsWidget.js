import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Bell, Flame, AlertTriangle, Calendar, CheckSquare, Mail,
  User, TrendingUp, ChevronRight, RefreshCw, Check, ExternalLink,
  Smartphone, X
} from 'lucide-react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const NotificationStatsWidget = () => {
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [stats, setStats] = useState({
    hot_leads: 0,
    stale_deals: 0,
    tasks_due: 0,
    meetings_today: 0
  });
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [pushStatus, setPushStatus] = useState(null);

  const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return { headers: { Authorization: `Bearer ${token}` } };
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [notifRes, pushRes] = await Promise.all([
        axios.get(`${API_URL}/api/notifications?limit=5`, getAuthHeaders()),
        axios.get(`${API_URL}/api/push/status`, getAuthHeaders()).catch(() => ({ data: null }))
      ]);
      
      setNotifications(notifRes.data.notifications || []);
      setUnreadCount(notifRes.data.unread_count || 0);
      setPushStatus(pushRes.data);
      
      // Calculate stats from notifications
      const notifs = notifRes.data.notifications || [];
      setStats({
        hot_leads: notifs.filter(n => n.type === 'hot_lead' && !n.read).length,
        stale_deals: notifs.filter(n => n.type === 'stale_deal' && !n.read).length,
        tasks_due: notifs.filter(n => n.type === 'task_due' && !n.read).length,
        meetings_today: notifs.filter(n => n.type === 'meeting_reminder' && !n.read).length
      });
    } catch (error) {
      console.error('Failed to fetch notification data');
    } finally {
      setLoading(false);
    }
  };

  const refreshNotifications = async () => {
    setRefreshing(true);
    try {
      const response = await axios.get(`${API_URL}/api/notifications/generate`, getAuthHeaders());
      if (response.data.notifications_created > 0) {
        toast.success(`Generated ${response.data.notifications_created} new alerts`);
        fetchData();
      } else {
        toast.info('No new alerts');
      }
    } catch (error) {
      toast.error('Failed to refresh');
    } finally {
      setRefreshing(false);
    }
  };

  const markAllRead = async () => {
    try {
      await axios.post(`${API_URL}/api/notifications/mark-read`, { mark_all: true }, getAuthHeaders());
      setNotifications(prev => prev.map(n => ({ ...n, read: true })));
      setUnreadCount(0);
      toast.success('All notifications marked as read');
    } catch (error) {
      toast.error('Failed to mark as read');
    }
  };

  const getTypeIcon = (type) => {
    switch (type) {
      case 'hot_lead': return <Flame className="w-4 h-4 text-orange-500" />;
      case 'stale_deal': return <AlertTriangle className="w-4 h-4 text-yellow-500" />;
      case 'meeting_reminder': return <Calendar className="w-4 h-4 text-purple-500" />;
      case 'task_due': return <CheckSquare className="w-4 h-4 text-green-500" />;
      case 'email_opened': return <Mail className="w-4 h-4 text-blue-500" />;
      case 'new_lead_assigned': return <User className="w-4 h-4 text-primary" />;
      default: return <Bell className="w-4 h-4 text-slate-400" />;
    }
  };

  const formatTime = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return date.toLocaleDateString();
  };

  const quickStats = [
    { icon: Flame, label: 'Hot Leads', value: stats.hot_leads, color: 'text-orange-500', bg: 'bg-orange-100' },
    { icon: AlertTriangle, label: 'Stale Deals', value: stats.stale_deals, color: 'text-yellow-500', bg: 'bg-yellow-100' },
    { icon: CheckSquare, label: 'Tasks Due', value: stats.tasks_due, color: 'text-green-500', bg: 'bg-green-100' },
    { icon: Calendar, label: 'Meetings', value: stats.meetings_today, color: 'text-purple-500', bg: 'bg-purple-100' }
  ];

  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-border p-6 animate-pulse">
        <div className="h-6 bg-slate-200 rounded w-1/3 mb-4"></div>
        <div className="space-y-3">
          <div className="h-16 bg-slate-100 rounded"></div>
          <div className="h-16 bg-slate-100 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-xl border border-border overflow-hidden"
    >
      {/* Header */}
      <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-gradient-to-r from-slate-50 to-white">
        <div className="flex items-center gap-3">
          <div className="relative">
            <Bell className="w-5 h-5 text-primary" />
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </div>
          <div>
            <h3 className="font-semibold text-foreground">Smart Alerts</h3>
            <p className="text-xs text-secondary">{unreadCount} unread notifications</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={refreshNotifications}
            disabled={refreshing}
            className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
            title="Refresh alerts"
          >
            <RefreshCw className={`w-4 h-4 text-secondary ${refreshing ? 'animate-spin' : ''}`} />
          </button>
          {unreadCount > 0 && (
            <button
              onClick={markAllRead}
              className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
              title="Mark all as read"
            >
              <Check className="w-4 h-4 text-secondary" />
            </button>
          )}
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-4 gap-2 p-4 bg-slate-50/50">
        {quickStats.map((stat, idx) => (
          <motion.div
            key={idx}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: idx * 0.05 }}
            className="text-center p-2 rounded-lg hover:bg-white transition-colors cursor-pointer"
            onClick={() => navigate('/leads')}
          >
            <div className={`w-8 h-8 ${stat.bg} rounded-lg flex items-center justify-center mx-auto mb-1`}>
              <stat.icon className={`w-4 h-4 ${stat.color}`} />
            </div>
            <p className="text-lg font-bold text-foreground">{stat.value}</p>
            <p className="text-[10px] text-secondary">{stat.label}</p>
          </motion.div>
        ))}
      </div>

      {/* Push Status Banner */}
      {pushStatus && !pushStatus.push_enabled && (
        <div className="px-4 py-2 bg-blue-50 border-y border-blue-100 flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm text-blue-700">
            <Smartphone className="w-4 h-4" />
            <span>Enable push for alerts when tab is closed</span>
          </div>
          <button
            onClick={() => navigate('/settings/notifications')}
            className="text-xs font-medium text-blue-600 hover:underline"
          >
            Enable
          </button>
        </div>
      )}

      {/* Recent Notifications */}
      <div className="divide-y divide-border">
        {notifications.length === 0 ? (
          <div className="p-6 text-center">
            <Bell className="w-10 h-10 text-slate-200 mx-auto mb-2" />
            <p className="text-secondary text-sm">No recent alerts</p>
            <button
              onClick={refreshNotifications}
              className="mt-2 text-sm text-primary hover:underline"
            >
              Check for alerts
            </button>
          </div>
        ) : (
          <AnimatePresence>
            {notifications.slice(0, 4).map((notif, idx) => (
              <motion.div
                key={notif.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: idx * 0.05 }}
                onClick={() => {
                  if (notif.lead_id) navigate(`/leads/${notif.lead_id}`);
                  else if (notif.type === 'meeting_reminder') navigate('/calendar');
                  else if (notif.type === 'task_due') navigate('/tasks');
                }}
                className={`px-4 py-3 flex items-start gap-3 cursor-pointer hover:bg-slate-50 transition-colors ${
                  !notif.read ? 'bg-blue-50/50' : ''
                }`}
              >
                <div className="flex-shrink-0 mt-0.5">
                  {getTypeIcon(notif.type)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className={`text-sm truncate ${!notif.read ? 'font-medium text-foreground' : 'text-secondary'}`}>
                    {notif.title?.replace(/^[^\s]+\s/, '')}
                  </p>
                  <p className="text-xs text-secondary truncate mt-0.5">{notif.message}</p>
                </div>
                <div className="flex-shrink-0 flex items-center gap-2">
                  <span className="text-[10px] text-secondary">{formatTime(notif.created_at)}</span>
                  {!notif.read && <span className="w-2 h-2 bg-blue-500 rounded-full" />}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-border bg-slate-50/50 flex items-center justify-between">
        <button
          onClick={() => navigate('/settings/notifications')}
          className="text-xs text-secondary hover:text-foreground transition-colors"
        >
          Notification settings
        </button>
        <button
          onClick={() => {
            const bellButton = document.querySelector('[data-testid="notification-bell"]');
            if (bellButton) bellButton.click();
          }}
          className="text-xs text-primary font-medium hover:underline flex items-center gap-1"
        >
          View all <ChevronRight className="w-3 h-3" />
        </button>
      </div>
    </motion.div>
  );
};

export default NotificationStatsWidget;
