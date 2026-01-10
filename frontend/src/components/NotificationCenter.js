import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Bell, X, AlertTriangle, AlertCircle, Info, CheckCircle,
  ExternalLink, Clock, Trash2, RefreshCw, Flame, Calendar,
  CheckSquare, Mail, User
} from 'lucide-react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const NotificationCenter = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const dropdownRef = useRef(null);
  const navigate = useNavigate();

  const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return { headers: { Authorization: `Bearer ${token}` } };
  };

  const fetchNotifications = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) return;

      const response = await axios.get(`${API_URL}/api/notifications`, getAuthHeaders());
      setNotifications(response.data.notifications || []);
      setUnreadCount(response.data.unread_count || 0);
    } catch (err) {
      console.error('Failed to fetch notifications:', err);
    }
  };

  const generateNotifications = async () => {
    setGenerating(true);
    try {
      const response = await axios.get(`${API_URL}/api/notifications/generate`, getAuthHeaders());
      if (response.data.notifications_created > 0) {
        toast.success(`Generated ${response.data.notifications_created} new notifications`);
        fetchNotifications();
      } else {
        toast.info('No new notifications to generate');
      }
    } catch (err) {
      console.error('Failed to generate notifications:', err);
    } finally {
      setGenerating(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
    // Generate notifications on first load
    generateNotifications();
    
    // Poll for new notifications every 60 seconds
    const interval = setInterval(() => {
      fetchNotifications();
      generateNotifications();
    }, 60000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const markAsRead = async (notificationIds, markAll = false) => {
    try {
      await axios.post(
        `${API_URL}/api/notifications/mark-read`,
        { notification_ids: notificationIds, mark_all: markAll },
        getAuthHeaders()
      );
      
      if (markAll) {
        setNotifications(prev => prev.map(n => ({ ...n, read: true })));
        setUnreadCount(0);
      } else {
        setNotifications(prev => 
          prev.map(n => notificationIds.includes(n.id) ? { ...n, read: true } : n)
        );
        setUnreadCount(prev => Math.max(0, prev - notificationIds.length));
      }
    } catch (err) {
      console.error('Failed to mark notification as read:', err);
    }
  };

  const deleteNotification = async (notificationId, e) => {
    e.stopPropagation();
    try {
      await axios.delete(`${API_URL}/api/notifications/${notificationId}`, getAuthHeaders());
      setNotifications(prev => prev.filter(n => n.id !== notificationId));
      const deleted = notifications.find(n => n.id === notificationId);
      if (deleted && !deleted.read) {
        setUnreadCount(prev => Math.max(0, prev - 1));
      }
    } catch (err) {
      console.error('Failed to delete notification:', err);
    }
  };

  const handleNotificationClick = (notification) => {
    markAsRead([notification.id]);
    
    // Navigate based on notification type
    if (notification.lead_id) {
      navigate(`/leads/${notification.lead_id}`);
      setIsOpen(false);
    } else if (notification.type === 'meeting_reminder' && notification.data?.event_id) {
      navigate('/calendar');
      setIsOpen(false);
    } else if (notification.type === 'task_due') {
      navigate('/tasks');
      setIsOpen(false);
    }
  };

  const getTypeIcon = (type) => {
    switch (type) {
      case 'hot_lead':
        return <Flame className="w-5 h-5 text-orange-500" />;
      case 'stale_deal':
        return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
      case 'email_opened':
        return <Mail className="w-5 h-5 text-blue-500" />;
      case 'meeting_reminder':
        return <Calendar className="w-5 h-5 text-purple-500" />;
      case 'task_due':
        return <CheckSquare className="w-5 h-5 text-green-500" />;
      case 'new_lead_assigned':
        return <User className="w-5 h-5 text-primary" />;
      default:
        return <Info className="w-5 h-5 text-secondary" />;
    }
  };

  const getTypeBg = (type) => {
    switch (type) {
      case 'hot_lead':
        return 'bg-orange-50 border-orange-200';
      case 'stale_deal':
        return 'bg-yellow-50 border-yellow-200';
      case 'email_opened':
        return 'bg-blue-50 border-blue-200';
      case 'meeting_reminder':
        return 'bg-purple-50 border-purple-200';
      case 'task_due':
        return 'bg-green-50 border-green-200';
      default:
        return 'bg-slate-50 border-slate-200';
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

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell Icon */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 hover:bg-slate-100 rounded-lg transition-colors"
        data-testid="notification-bell"
      >
        <Bell className="w-5 h-5 text-secondary" />
        {unreadCount > 0 && (
          <motion.span
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs font-bold rounded-full flex items-center justify-center"
          >
            {unreadCount > 9 ? '9+' : unreadCount}
          </motion.span>
        )}
      </button>

      {/* Dropdown */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="absolute right-0 mt-2 w-96 max-w-[calc(100vw-2rem)] bg-white rounded-xl shadow-xl border border-border overflow-hidden z-50"
          >
            {/* Header */}
            <div className="px-4 py-3 border-b border-border flex items-center justify-between bg-slate-50">
              <div className="flex items-center gap-2">
                <h3 className="font-semibold text-foreground">Smart Notifications</h3>
                {unreadCount > 0 && (
                  <span className="px-2 py-0.5 bg-red-100 text-red-600 text-xs rounded-full">
                    {unreadCount} new
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={generateNotifications}
                  disabled={generating}
                  className="p-1.5 hover:bg-slate-200 rounded-lg transition-colors"
                  title="Refresh notifications"
                >
                  <RefreshCw className={`w-4 h-4 text-secondary ${generating ? 'animate-spin' : ''}`} />
                </button>
                {unreadCount > 0 && (
                  <button
                    onClick={() => markAsRead([], true)}
                    className="text-xs text-primary hover:underline"
                  >
                    Mark all read
                  </button>
                )}
              </div>
            </div>

            {/* Notifications List */}
            <div className="max-h-96 overflow-y-auto">
              {notifications.length === 0 ? (
                <div className="p-8 text-center">
                  <Bell className="w-12 h-12 text-secondary/30 mx-auto mb-3" />
                  <p className="text-secondary text-sm">No notifications yet</p>
                  <p className="text-xs text-secondary/70 mt-1">We'll alert you about hot leads, stale deals, and more</p>
                </div>
              ) : (
                <div className="divide-y divide-border">
                  {notifications.map((notification) => (
                    <motion.div
                      key={notification.id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      onClick={() => handleNotificationClick(notification)}
                      className={`p-4 cursor-pointer hover:bg-slate-50 transition-colors group ${
                        !notification.read ? 'bg-blue-50/50' : ''
                      }`}
                    >
                      <div className="flex gap-3">
                        <div className={`flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center border ${getTypeBg(notification.type)}`}>
                          {getTypeIcon(notification.type)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-start justify-between gap-2">
                            <h4 className={`text-sm font-medium ${!notification.read ? 'text-foreground' : 'text-secondary'}`}>
                              {notification.title}
                            </h4>
                            <div className="flex items-center gap-1">
                              {!notification.read && (
                                <span className="w-2 h-2 bg-blue-500 rounded-full flex-shrink-0" />
                              )}
                              <button
                                onClick={(e) => deleteNotification(notification.id, e)}
                                className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-100 rounded transition-all"
                              >
                                <Trash2 className="w-3 h-3 text-red-500" />
                              </button>
                            </div>
                          </div>
                          <p className="text-xs text-secondary mt-1 line-clamp-2">
                            {notification.message}
                          </p>
                          <div className="flex items-center gap-2 mt-2">
                            <Clock className="w-3 h-3 text-secondary/50" />
                            <span className="text-xs text-secondary/70">
                              {formatTime(notification.created_at)}
                            </span>
                            {notification.lead_id && (
                              <span className="text-xs text-primary ml-auto">View lead →</span>
                            )}
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="px-4 py-3 border-t border-border bg-slate-50 flex items-center justify-between">
              <span className="text-xs text-secondary">Auto-refreshes every minute</span>
              <button
                onClick={() => {
                  navigate('/settings/notifications');
                  setIsOpen(false);
                }}
                className="text-xs text-primary hover:underline"
              >
                Notification settings
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default NotificationCenter;
