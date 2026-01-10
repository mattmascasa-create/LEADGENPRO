import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  Bell, Flame, AlertTriangle, Mail, Calendar, CheckSquare,
  User, TrendingUp, Moon, Clock, ArrowLeft, Save, Loader2,
  Smartphone, Send, ExternalLink
} from 'lucide-react';
import axios from 'axios';
import { toast } from 'react-toastify';
import { useNavigate } from 'react-router-dom';
import DashboardLayout from '@/components/DashboardLayout';
import { 
  isPushSupported, 
  getNotificationPermission, 
  subscribeToPushNotifications,
  unsubscribeFromPushNotifications,
  isSubscribedToPush 
} from '@/utils/pushNotifications';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const NotificationPreferencesPage = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [pushSupported, setPushSupported] = useState(false);
  const [pushPermission, setPushPermission] = useState('default');
  const [pushSubscribed, setPushSubscribed] = useState(false);
  const [togglingPush, setTogglingPush] = useState(false);
  const [testingPush, setTestingPush] = useState(false);
  const [preferences, setPreferences] = useState({
    hot_lead_alerts: true,
    stale_deal_alerts: true,
    email_opened_alerts: true,
    meeting_reminders: true,
    task_due_alerts: true,
    new_lead_assigned: true,
    deal_stage_change: true,
    quiet_hours_enabled: false,
    quiet_hours_start: "22:00",
    quiet_hours_end: "08:00",
    email_digest: false
  });
  const [sendingDigest, setSendingDigest] = useState(false);

  const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return { headers: { Authorization: `Bearer ${token}` } };
  };

  useEffect(() => {
    fetchPreferences();
    checkPushStatus();
  }, []);

  const checkPushStatus = async () => {
    setPushSupported(isPushSupported());
    setPushPermission(getNotificationPermission());
    const subscribed = await isSubscribedToPush();
    setPushSubscribed(subscribed);
  };

  const fetchPreferences = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/notifications/preferences`, getAuthHeaders());
      setPreferences(prev => ({ ...prev, ...response.data }));
    } catch (error) {
      console.error('Failed to fetch preferences');
    } finally {
      setLoading(false);
    }
  };

  const savePreferences = async () => {
    setSaving(true);
    try {
      await axios.put(`${API_URL}/api/notifications/preferences`, preferences, getAuthHeaders());
      toast.success('Notification preferences saved!');
    } catch (error) {
      toast.error('Failed to save preferences');
    } finally {
      setSaving(false);
    }
  };

  const togglePushNotifications = async () => {
    setTogglingPush(true);
    try {
      const token = localStorage.getItem('token');
      if (pushSubscribed) {
        await unsubscribeFromPushNotifications(token);
        setPushSubscribed(false);
        toast.success('Push notifications disabled');
      } else {
        await subscribeToPushNotifications(token);
        setPushSubscribed(true);
        setPushPermission('granted');
        toast.success('Push notifications enabled! You\'ll now receive alerts even when the tab is closed.');
      }
    } catch (error) {
      console.error('Push toggle error:', error);
      if (error.message.includes('denied')) {
        toast.error('Notification permission denied. Please enable in browser settings.');
      } else {
        toast.error('Failed to toggle push notifications');
      }
    } finally {
      setTogglingPush(false);
    }
  };

  const sendTestPush = async () => {
    setTestingPush(true);
    try {
      const response = await axios.post(`${API_URL}/api/push/test`, {}, getAuthHeaders());
      toast.success(`Test notification sent to ${response.data.sent} device(s)!`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send test notification');
    } finally {
      setTestingPush(false);
    }
  };

  const sendTestDigest = async () => {
    setSendingDigest(true);
    try {
      const response = await axios.post(`${API_URL}/api/notifications/send-digest`, {}, getAuthHeaders());
      toast.success(response.data.message);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send digest email');
    } finally {
      setSendingDigest(false);
    }
  };

  const previewDigest = () => {
    const token = localStorage.getItem('token');
    window.open(`${API_URL}/api/notifications/digest-preview?token=${token}`, '_blank');
  };

  const togglePreference = (key) => {
    setPreferences(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const notificationTypes = [
    {
      key: 'hot_lead_alerts',
      icon: Flame,
      iconColor: 'text-orange-500',
      iconBg: 'bg-orange-100',
      title: 'Hot Lead Alerts',
      description: 'Get notified when high-score leads need attention'
    },
    {
      key: 'stale_deal_alerts',
      icon: AlertTriangle,
      iconColor: 'text-yellow-500',
      iconBg: 'bg-yellow-100',
      title: 'Stale Deal Alerts',
      description: 'Alert when deals are stuck in proposal/negotiation too long'
    },
    {
      key: 'email_opened_alerts',
      icon: Mail,
      iconColor: 'text-blue-500',
      iconBg: 'bg-blue-100',
      title: 'Email Opened',
      description: 'Know when leads open your emails'
    },
    {
      key: 'meeting_reminders',
      icon: Calendar,
      iconColor: 'text-purple-500',
      iconBg: 'bg-purple-100',
      title: 'Meeting Reminders',
      description: 'Reminders for upcoming meetings'
    },
    {
      key: 'task_due_alerts',
      icon: CheckSquare,
      iconColor: 'text-green-500',
      iconBg: 'bg-green-100',
      title: 'Task Due Alerts',
      description: 'Alerts for tasks due today'
    },
    {
      key: 'new_lead_assigned',
      icon: User,
      iconColor: 'text-primary',
      iconBg: 'bg-blue-100',
      title: 'New Lead Assigned',
      description: 'Get notified when a lead is assigned to you'
    },
    {
      key: 'deal_stage_change',
      icon: TrendingUp,
      iconColor: 'text-emerald-500',
      iconBg: 'bg-emerald-100',
      title: 'Deal Stage Changes',
      description: 'Track when deals move through pipeline stages'
    }
  ];

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/settings')}
              className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-2xl font-bold">Notification Preferences</h1>
              <p className="text-secondary text-sm">Customize which alerts you receive</p>
            </div>
          </div>
          <button
            onClick={savePreferences}
            disabled={saving}
            className="px-4 py-2 bg-primary text-white rounded-lg font-medium hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2"
            data-testid="save-preferences-btn"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Save Changes
          </button>
        </div>

        {/* Notification Types */}
        <div className="bg-white rounded-xl border border-border overflow-hidden mb-6">
          <div className="px-6 py-4 border-b border-border bg-slate-50">
            <div className="flex items-center gap-2">
              <Bell className="w-5 h-5 text-primary" />
              <h2 className="font-semibold">Alert Types</h2>
            </div>
            <p className="text-sm text-secondary mt-1">Choose which notifications you want to receive</p>
          </div>
          
          <div className="divide-y divide-border">
            {notificationTypes.map((type, idx) => (
              <motion.div
                key={type.key}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.05 }}
                className="px-6 py-4 flex items-center justify-between hover:bg-slate-50 transition-colors"
              >
                <div className="flex items-center gap-4">
                  <div className={`w-10 h-10 rounded-lg ${type.iconBg} flex items-center justify-center`}>
                    <type.icon className={`w-5 h-5 ${type.iconColor}`} />
                  </div>
                  <div>
                    <h3 className="font-medium">{type.title}</h3>
                    <p className="text-sm text-secondary">{type.description}</p>
                  </div>
                </div>
                <button
                  onClick={() => togglePreference(type.key)}
                  className={`w-12 h-7 rounded-full transition-colors relative ${
                    preferences[type.key] ? 'bg-primary' : 'bg-slate-300'
                  }`}
                  data-testid={`toggle-${type.key}`}
                >
                  <div className={`w-5 h-5 bg-white rounded-full shadow-md absolute top-1 transition-transform ${
                    preferences[type.key] ? 'translate-x-6' : 'translate-x-1'
                  }`} />
                </button>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Browser Push Notifications */}
        <div className="bg-white rounded-xl border border-border overflow-hidden mb-6">
          <div className="px-6 py-4 border-b border-border bg-slate-50">
            <div className="flex items-center gap-2">
              <Smartphone className="w-5 h-5 text-green-500" />
              <h2 className="font-semibold">Browser Push Notifications</h2>
            </div>
            <p className="text-sm text-secondary mt-1">Get alerts even when the browser tab is closed</p>
          </div>
          
          <div className="p-6">
            {!pushSupported ? (
              <div className="text-center py-4">
                <AlertTriangle className="w-10 h-10 text-yellow-500 mx-auto mb-2" />
                <p className="text-secondary">Push notifications are not supported in your browser</p>
              </div>
            ) : pushPermission === 'denied' ? (
              <div className="text-center py-4">
                <AlertTriangle className="w-10 h-10 text-red-500 mx-auto mb-2" />
                <p className="text-secondary">Notifications blocked. Please enable in browser settings.</p>
                <p className="text-xs text-secondary mt-2">
                  Click the lock icon in your address bar → Site settings → Allow notifications
                </p>
              </div>
            ) : (
              <>
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center">
                      <Bell className="w-5 h-5 text-green-500" />
                    </div>
                    <div>
                      <h3 className="font-medium">Enable Push Notifications</h3>
                      <p className="text-sm text-secondary">Receive alerts on your device</p>
                    </div>
                  </div>
                  <button
                    onClick={togglePushNotifications}
                    disabled={togglingPush}
                    className={`w-12 h-7 rounded-full transition-colors relative ${
                      pushSubscribed ? 'bg-green-500' : 'bg-slate-300'
                    }`}
                    data-testid="toggle-push"
                  >
                    {togglingPush ? (
                      <Loader2 className="w-4 h-4 animate-spin absolute top-1.5 left-4 text-white" />
                    ) : (
                      <div className={`w-5 h-5 bg-white rounded-full shadow-md absolute top-1 transition-transform ${
                        pushSubscribed ? 'translate-x-6' : 'translate-x-1'
                      }`} />
                    )}
                  </button>
                </div>
                
                {pushSubscribed && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex items-center justify-between pt-4 border-t border-border"
                  >
                    <div>
                      <p className="text-sm text-green-600 flex items-center gap-2">
                        <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                        Push notifications active
                      </p>
                      <p className="text-xs text-secondary mt-1">Test your setup with a sample notification</p>
                    </div>
                    <button
                      onClick={sendTestPush}
                      disabled={testingPush}
                      className="px-3 py-1.5 bg-green-100 text-green-700 rounded-lg text-sm font-medium hover:bg-green-200 disabled:opacity-50 flex items-center gap-2"
                    >
                      {testingPush ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                      Send Test
                    </button>
                  </motion.div>
                )}
              </>
            )}
          </div>
        </div>

        {/* Quiet Hours */}
        <div className="bg-white rounded-xl border border-border overflow-hidden mb-6">
          <div className="px-6 py-4 border-b border-border bg-slate-50">
            <div className="flex items-center gap-2">
              <Moon className="w-5 h-5 text-indigo-500" />
              <h2 className="font-semibold">Quiet Hours</h2>
            </div>
            <p className="text-sm text-secondary mt-1">Pause notifications during specific hours</p>
          </div>
          
          <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-indigo-100 flex items-center justify-center">
                  <Moon className="w-5 h-5 text-indigo-500" />
                </div>
                <div>
                  <h3 className="font-medium">Enable Quiet Hours</h3>
                  <p className="text-sm text-secondary">No notifications during set times</p>
                </div>
              </div>
              <button
                onClick={() => togglePreference('quiet_hours_enabled')}
                className={`w-12 h-7 rounded-full transition-colors relative ${
                  preferences.quiet_hours_enabled ? 'bg-primary' : 'bg-slate-300'
                }`}
                data-testid="toggle-quiet-hours"
              >
                <div className={`w-5 h-5 bg-white rounded-full shadow-md absolute top-1 transition-transform ${
                  preferences.quiet_hours_enabled ? 'translate-x-6' : 'translate-x-1'
                }`} />
              </button>
            </div>

            {preferences.quiet_hours_enabled && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                className="flex items-center gap-4 pt-4 border-t border-border"
              >
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-secondary" />
                  <span className="text-sm text-secondary">From</span>
                </div>
                <input
                  type="time"
                  value={preferences.quiet_hours_start}
                  onChange={(e) => setPreferences(prev => ({ ...prev, quiet_hours_start: e.target.value }))}
                  className="px-3 py-2 border border-border rounded-lg text-sm"
                />
                <span className="text-sm text-secondary">to</span>
                <input
                  type="time"
                  value={preferences.quiet_hours_end}
                  onChange={(e) => setPreferences(prev => ({ ...prev, quiet_hours_end: e.target.value }))}
                  className="px-3 py-2 border border-border rounded-lg text-sm"
                />
              </motion.div>
            )}
          </div>
        </div>

        {/* Email Digest */}
        <div className="bg-white rounded-xl border border-border overflow-hidden">
          <div className="px-6 py-4 border-b border-border bg-slate-50">
            <div className="flex items-center gap-2">
              <Mail className="w-5 h-5 text-blue-500" />
              <h2 className="font-semibold">Email Digest</h2>
            </div>
            <p className="text-sm text-secondary mt-1">Receive a daily summary by email</p>
          </div>
          
          <div className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
                  <Mail className="w-5 h-5 text-blue-500" />
                </div>
                <div>
                  <h3 className="font-medium">Daily Email Summary</h3>
                  <p className="text-sm text-secondary">Get a digest of all notifications each morning</p>
                </div>
              </div>
              <button
                onClick={() => togglePreference('email_digest')}
                className={`w-12 h-7 rounded-full transition-colors relative ${
                  preferences.email_digest ? 'bg-primary' : 'bg-slate-300'
                }`}
                data-testid="toggle-email-digest"
              >
                <div className={`w-5 h-5 bg-white rounded-full shadow-md absolute top-1 transition-transform ${
                  preferences.email_digest ? 'translate-x-6' : 'translate-x-1'
                }`} />
              </button>
            </div>

            {preferences.email_digest && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="pt-4 border-t border-border"
              >
                <p className="text-sm text-green-600 flex items-center gap-2 mb-3">
                  <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                  Daily digest enabled - sent every morning at 8 AM
                </p>
                <div className="flex gap-3">
                  <button
                    onClick={sendTestDigest}
                    disabled={sendingDigest}
                    className="px-4 py-2 bg-blue-100 text-blue-700 rounded-lg text-sm font-medium hover:bg-blue-200 disabled:opacity-50 flex items-center gap-2"
                  >
                    {sendingDigest ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                    Send Test Digest
                  </button>
                  <button
                    onClick={() => window.open(`${API_URL}/api/notifications/digest-preview`, '_blank')}
                    className="px-4 py-2 border border-border rounded-lg text-sm font-medium hover:bg-slate-50 flex items-center gap-2"
                  >
                    <ExternalLink className="w-4 h-4" />
                    Preview
                  </button>
                </div>
              </motion.div>
            )}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="mt-6 flex justify-center gap-4">
          <button
            onClick={() => {
              setPreferences(prev => Object.keys(prev).reduce((acc, key) => {
                if (typeof prev[key] === 'boolean' && key !== 'quiet_hours_enabled' && key !== 'email_digest') {
                  acc[key] = true;
                } else {
                  acc[key] = prev[key];
                }
                return acc;
              }, {}));
            }}
            className="text-sm text-primary hover:underline"
          >
            Enable all alerts
          </button>
          <span className="text-slate-300">|</span>
          <button
            onClick={() => {
              setPreferences(prev => Object.keys(prev).reduce((acc, key) => {
                if (typeof prev[key] === 'boolean' && key !== 'quiet_hours_enabled' && key !== 'email_digest') {
                  acc[key] = false;
                } else {
                  acc[key] = prev[key];
                }
                return acc;
              }, {}));
            }}
            className="text-sm text-red-500 hover:underline"
          >
            Disable all alerts
          </button>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default NotificationPreferencesPage;
