import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Key, Plus, Copy, Trash2, Eye, EyeOff, Shield, 
  Settings, Phone, Bell, Link2, Code, CheckCircle,
  AlertCircle, Loader2, RefreshCw, ExternalLink,
  HardDrive, Calendar, Video, Mail, User as UserIcon,
  ArrowLeftRight, Clock
} from 'lucide-react';
import { toast } from 'react-toastify';
import DashboardLayout from '@/components/DashboardLayout';
import { useAuth } from '@/context/AuthContext';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const SettingsPage = () => {
  const { user, refreshUser } = useAuth();
  const [activeTab, setActiveTab] = useState('profile');
  const [apiKeys, setApiKeys] = useState([]);
  const [showNewKeyModal, setShowNewKeyModal] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [newKeyPermissions, setNewKeyPermissions] = useState(['read']);
  const [createdKey, setCreatedKey] = useState(null);
  const [loading, setLoading] = useState(false);
  const [googleStatus, setGoogleStatus] = useState(null);
  const [connectingGoogle, setConnectingGoogle] = useState(false);
  const [calendarSyncStatus, setCalendarSyncStatus] = useState(null);
  const [syncing, setSyncing] = useState(false);
  const [profileForm, setProfileForm] = useState({
    full_name: '',
    phone: '',
    company: '',
    department: ''
  });
  const [savingProfile, setSavingProfile] = useState(false);
  const [autoSyncStatus, setAutoSyncStatus] = useState(null);
  const [togglingAutoSync, setTogglingAutoSync] = useState(false);

  useEffect(() => {
    if (user) {
      setProfileForm({
        full_name: user.full_name || '',
        phone: user.phone || '',
        company: user.company || '',
        department: user.department || ''
      });
    }
  }, [user]);

  useEffect(() => {
    if (activeTab === 'api') {
      fetchApiKeys();
    }
    if (activeTab === 'integrations') {
      fetchGoogleStatus();
      fetchCalendarSyncStatus();
      fetchAutoSyncStatus();
    }
  }, [activeTab]);

  useEffect(() => {
    // Check for Google connection result from URL
    const params = new URLSearchParams(window.location.search);
    if (params.get('google') === 'connected') {
      toast.success('Google account connected successfully!');
      setActiveTab('integrations');
      fetchGoogleStatus();
      window.history.replaceState({}, '', '/settings');
    }
    if (params.get('error')) {
      toast.error(`Google connection failed: ${params.get('error')}`);
      window.history.replaceState({}, '', '/settings');
    }
  }, []);

  const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return { headers: { Authorization: `Bearer ${token}` } };
  };

  const fetchGoogleStatus = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/google/status`, getAuthHeaders());
      setGoogleStatus(response.data);
    } catch (error) {
      console.error('Failed to fetch Google status');
    }
  };

  const connectGoogle = async (services = 'drive,calendar') => {
    setConnectingGoogle(true);
    try {
      const response = await axios.get(
        `${API_URL}/api/google/connect?services=${services}`,
        getAuthHeaders()
      );
      if (response.data.auth_url) {
        window.location.href = response.data.auth_url;
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to initiate Google connection');
      setConnectingGoogle(false);
    }
  };

  const disconnectGoogle = async () => {
    if (!window.confirm('Are you sure you want to disconnect your Google account?')) return;
    
    try {
      await axios.post(`${API_URL}/api/google/disconnect`, {}, getAuthHeaders());
      setGoogleStatus({ connected: false });
      setCalendarSyncStatus(null);
      toast.success('Google account disconnected');
    } catch (error) {
      toast.error('Failed to disconnect Google account');
    }
  };

  const fetchCalendarSyncStatus = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/google/calendar/sync-status`, getAuthHeaders());
      setCalendarSyncStatus(response.data);
    } catch (error) {
      console.error('Failed to fetch calendar sync status');
    }
  };

  const syncCalendar = async (direction = 'both') => {
    setSyncing(true);
    try {
      const response = await axios.post(
        `${API_URL}/api/google/calendar/sync`,
        { sync_direction: direction, days_ahead: 30, days_back: 7 },
        getAuthHeaders()
      );
      toast.success(response.data.message);
      fetchCalendarSyncStatus();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Calendar sync failed');
    } finally {
      setSyncing(false);
    }
  };

  const fetchAutoSyncStatus = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/google/calendar/auto-sync/status`, getAuthHeaders());
      setAutoSyncStatus(response.data);
    } catch (error) {
      console.error('Failed to fetch auto-sync status');
    }
  };

  const toggleAutoSync = async () => {
    setTogglingAutoSync(true);
    try {
      if (autoSyncStatus?.auto_sync_enabled) {
        await axios.delete(`${API_URL}/api/google/calendar/auto-sync`, getAuthHeaders());
        toast.success('Automatic sync disabled');
      } else {
        await axios.post(`${API_URL}/api/google/calendar/auto-sync`, {}, getAuthHeaders());
        toast.success('Automatic sync enabled (every 15 minutes)');
      }
      fetchAutoSyncStatus();
    } catch (error) {
      toast.error('Failed to toggle auto-sync');
    } finally {
      setTogglingAutoSync(false);
    }
  };

  const fetchApiKeys = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/api-keys`, getAuthHeaders());
      setApiKeys(response.data);
    } catch (error) {
      console.error('Failed to fetch API keys');
    }
  };

  const createApiKey = async () => {
    if (!newKeyName.trim()) {
      toast.error('Please enter a name for the API key');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(
        `${API_URL}/api/api-keys`,
        { name: newKeyName, permissions: newKeyPermissions },
        getAuthHeaders()
      );
      setCreatedKey(response.data);
      fetchApiKeys();
      toast.success('API key created!');
    } catch (error) {
      toast.error('Failed to create API key');
    } finally {
      setLoading(false);
    }
  };

  const deleteApiKey = async (keyId) => {
    if (!window.confirm('Are you sure you want to delete this API key?')) return;

    try {
      await axios.delete(`${API_URL}/api/api-keys/${keyId}`, getAuthHeaders());
      fetchApiKeys();
      toast.success('API key deleted');
    } catch (error) {
      toast.error('Failed to delete API key');
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard!');
  };

  const saveProfile = async () => {
    setSavingProfile(true);
    try {
      await axios.put(`${API_URL}/api/auth/profile`, profileForm, getAuthHeaders());
      toast.success('Profile updated!');
      if (refreshUser) refreshUser();
    } catch (error) {
      toast.error('Failed to update profile');
    } finally {
      setSavingProfile(false);
    }
  };

  const togglePermission = (perm) => {
    setNewKeyPermissions(prev => 
      prev.includes(perm) 
        ? prev.filter(p => p !== perm)
        : [...prev, perm]
    );
  };

  const permissions = [
    { id: 'read', label: 'Read', description: 'View leads, appointments, calls' },
    { id: 'write', label: 'Write', description: 'Create and update data' },
    { id: 'delete', label: 'Delete', description: 'Delete records' },
    { id: 'admin', label: 'Admin', description: 'Manage webhooks and settings' }
  ];

  return (
    <DashboardLayout>
      <div className="p-6 max-w-5xl mx-auto" data-testid="settings-page">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-foreground mb-2">Settings</h1>
          <p className="text-secondary">Manage your profile and integrations</p>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 border-b border-border">
          {[
            { id: 'profile', label: 'Profile', icon: Settings },
            { id: 'api', label: 'API Keys', icon: Key },
            { id: 'integrations', label: 'Integrations', icon: Link2 }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-3 border-b-2 -mb-px transition-colors ${
                activeTab === tab.id
                  ? 'border-primary text-primary'
                  : 'border-transparent text-secondary hover:text-foreground'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Profile Tab */}
        {activeTab === 'profile' && (
          <div className="bg-card rounded-xl border border-border p-6">
            <h2 className="text-xl font-semibold mb-6">Profile Settings</h2>
            
            <div className="grid md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium mb-2">Full Name</label>
                <input
                  type="text"
                  value={profileForm.full_name}
                  onChange={(e) => setProfileForm({...profileForm, full_name: e.target.value})}
                  className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">
                  Phone Number
                  <span className="text-xs text-secondary ml-2">(for Click-to-Call)</span>
                </label>
                <input
                  type="tel"
                  value={profileForm.phone}
                  onChange={(e) => setProfileForm({...profileForm, phone: e.target.value})}
                  placeholder="(555) 123-4567"
                  className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Company</label>
                <input
                  type="text"
                  value={profileForm.company}
                  onChange={(e) => setProfileForm({...profileForm, company: e.target.value})}
                  className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Department</label>
                <input
                  type="text"
                  value={profileForm.department}
                  onChange={(e) => setProfileForm({...profileForm, department: e.target.value})}
                  className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
            </div>

            <div className="mt-6 pt-6 border-t border-border">
              <button
                onClick={saveProfile}
                disabled={savingProfile}
                className="px-6 py-3 bg-primary text-white rounded-lg font-medium hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2"
              >
                {savingProfile ? <Loader2 className="w-5 h-5 animate-spin" /> : <CheckCircle className="w-5 h-5" />}
                Save Changes
              </button>
            </div>
          </div>
        )}

        {/* API Keys Tab */}
        {activeTab === 'api' && (
          <div className="space-y-6">
            {/* API Documentation Card */}
            <div className="bg-gradient-to-r from-blue-600 to-indigo-600 rounded-xl p-6 text-white">
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="text-xl font-semibold mb-2 flex items-center gap-2">
                    <Code className="w-5 h-5" />
                    Public API
                  </h2>
                  <p className="text-blue-100 mb-4">
                    Connect LeadGen Pro to your external tools, CRMs, or custom applications.
                  </p>
                  <div className="flex gap-3">
                    <a
                      href={`${API_URL}/api/public/docs`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-4 py-2 bg-white/20 hover:bg-white/30 rounded-lg text-sm font-medium flex items-center gap-2"
                    >
                      <ExternalLink className="w-4 h-4" />
                      View API Docs
                    </a>
                    <button
                      onClick={() => copyToClipboard(`${API_URL}/api/public`)}
                      className="px-4 py-2 bg-white/20 hover:bg-white/30 rounded-lg text-sm font-medium flex items-center gap-2"
                    >
                      <Copy className="w-4 h-4" />
                      Copy Base URL
                    </button>
                  </div>
                </div>
                <Shield className="w-12 h-12 text-blue-200" />
              </div>
            </div>

            {/* API Keys List */}
            <div className="bg-card rounded-xl border border-border">
              <div className="p-6 border-b border-border flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-semibold">Your API Keys</h2>
                  <p className="text-secondary text-sm">Manage keys for external integrations</p>
                </div>
                <button
                  onClick={() => {
                    setShowNewKeyModal(true);
                    setCreatedKey(null);
                    setNewKeyName('');
                    setNewKeyPermissions(['read']);
                  }}
                  className="px-4 py-2 bg-primary text-white rounded-lg font-medium hover:bg-primary/90 flex items-center gap-2"
                >
                  <Plus className="w-5 h-5" />
                  Create Key
                </button>
              </div>

              <div className="divide-y divide-border">
                {apiKeys.length === 0 ? (
                  <div className="p-12 text-center">
                    <Key className="w-12 h-12 text-secondary mx-auto mb-4" />
                    <p className="text-secondary">No API keys yet</p>
                    <p className="text-sm text-secondary mt-1">Create one to start integrating</p>
                  </div>
                ) : (
                  apiKeys.map((key) => (
                    <div key={key.id} className="p-4 flex items-center justify-between hover:bg-accent/5">
                      <div className="flex items-center gap-4">
                        <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center">
                          <Key className="w-5 h-5 text-primary" />
                        </div>
                        <div>
                          <p className="font-medium">{key.name}</p>
                          <p className="text-sm text-secondary font-mono">{key.key_preview}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="flex gap-1">
                          {key.permissions?.map(p => (
                            <span key={p} className="px-2 py-0.5 bg-accent/10 text-accent rounded text-xs capitalize">
                              {p}
                            </span>
                          ))}
                        </div>
                        <button
                          onClick={() => deleteApiKey(key.id)}
                          className="p-2 text-red-500 hover:bg-red-50 rounded-lg"
                        >
                          <Trash2 className="w-5 h-5" />
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}

        {/* Integrations Tab */}
        {activeTab === 'integrations' && (
          <div className="space-y-6">
            {/* Google Account Card */}
            <div className="bg-card rounded-xl border border-border overflow-hidden">
              <div className="p-6 border-b border-border bg-gradient-to-r from-blue-50 to-indigo-50">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="w-16 h-16 bg-white rounded-xl shadow-sm flex items-center justify-center">
                      <svg className="w-10 h-10" viewBox="0 0 24 24">
                        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                      </svg>
                    </div>
                    <div>
                      <h2 className="text-xl font-semibold">Google Account</h2>
                      <p className="text-secondary text-sm">Connect your Google account for Drive, Calendar & Meet</p>
                    </div>
                  </div>
                  {googleStatus?.connected && (
                    <div className="flex items-center gap-2 text-green-600">
                      <CheckCircle className="w-5 h-5" />
                      <span className="font-medium">Connected</span>
                    </div>
                  )}
                </div>
              </div>

              <div className="p-6">
                {googleStatus?.connected ? (
                  <div className="space-y-4">
                    <div className="flex items-center gap-4 p-4 bg-slate-50 rounded-lg">
                      {googleStatus.picture ? (
                        <img src={googleStatus.picture} alt="" className="w-12 h-12 rounded-full" />
                      ) : (
                        <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center">
                          <UserIcon className="w-6 h-6 text-primary" />
                        </div>
                      )}
                      <div>
                        <p className="font-semibold">{googleStatus.name}</p>
                        <p className="text-sm text-secondary">{googleStatus.email}</p>
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-4">
                      <div className={`p-4 rounded-lg border-2 ${googleStatus.services?.drive ? 'border-green-200 bg-green-50' : 'border-border'}`}>
                        <HardDrive className={`w-6 h-6 mb-2 ${googleStatus.services?.drive ? 'text-green-600' : 'text-slate-400'}`} />
                        <p className="font-medium">Drive</p>
                        <p className="text-xs text-secondary">{googleStatus.services?.drive ? 'Connected' : 'Not connected'}</p>
                      </div>
                      <div className={`p-4 rounded-lg border-2 ${googleStatus.services?.calendar ? 'border-green-200 bg-green-50' : 'border-border'}`}>
                        <Calendar className={`w-6 h-6 mb-2 ${googleStatus.services?.calendar ? 'text-green-600' : 'text-slate-400'}`} />
                        <p className="font-medium">Calendar</p>
                        <p className="text-xs text-secondary">{googleStatus.services?.calendar ? 'Connected' : 'Not connected'}</p>
                      </div>
                      <div className={`p-4 rounded-lg border-2 ${googleStatus.services?.meet ? 'border-green-200 bg-green-50' : 'border-border'}`}>
                        <Video className={`w-6 h-6 mb-2 ${googleStatus.services?.meet ? 'text-green-600' : 'text-slate-400'}`} />
                        <p className="font-medium">Meet</p>
                        <p className="text-xs text-secondary">{googleStatus.services?.meet ? 'Connected' : 'Not connected'}</p>
                      </div>
                    </div>

                    <div className="flex gap-3 pt-4">
                      <button
                        onClick={() => connectGoogle('drive,calendar')}
                        className="px-4 py-2 border border-border rounded-lg text-sm font-medium hover:bg-accent/5"
                      >
                        Update Permissions
                      </button>
                      <button
                        onClick={disconnectGoogle}
                        className="px-4 py-2 text-red-600 border border-red-200 rounded-lg text-sm font-medium hover:bg-red-50"
                      >
                        Disconnect
                      </button>
                    </div>

                    {/* Two-Way Calendar Sync Section */}
                    {googleStatus.services?.calendar && (
                      <div className="mt-6 pt-6 border-t border-border">
                        <div className="flex items-center justify-between mb-4">
                          <div className="flex items-center gap-3">
                            <ArrowLeftRight className="w-5 h-5 text-primary" />
                            <div>
                              <h3 className="font-semibold">Two-Way Calendar Sync</h3>
                              <p className="text-sm text-secondary">Sync events between LeadGen Pro and Google Calendar</p>
                            </div>
                          </div>
                          <button
                            onClick={() => syncCalendar('both')}
                            disabled={syncing}
                            className="px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2"
                            data-testid="sync-calendar-btn"
                          >
                            {syncing ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              <RefreshCw className="w-4 h-4" />
                            )}
                            Sync Now
                          </button>
                        </div>

                        {calendarSyncStatus && (
                          <div className="bg-slate-50 rounded-lg p-4 space-y-3">
                            <div className="grid grid-cols-2 gap-4 text-sm">
                              <div className="flex items-center gap-2">
                                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                                <span className="text-secondary">Events Synced:</span>
                                <span className="font-medium">{calendarSyncStatus.events_synced || 0}</span>
                              </div>
                              <div className="flex items-center gap-2">
                                <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
                                <span className="text-secondary">Pending:</span>
                                <span className="font-medium">{calendarSyncStatus.events_pending || 0}</span>
                              </div>
                            </div>
                            {calendarSyncStatus.last_sync && (
                              <div className="flex items-center gap-2 text-sm text-secondary">
                                <Clock className="w-4 h-4" />
                                Last synced: {new Date(calendarSyncStatus.last_sync).toLocaleString()}
                              </div>
                            )}
                            {calendarSyncStatus.sync_stats && (
                              <div className="text-xs text-secondary pt-2 border-t border-slate-200">
                                Last sync: Pushed {calendarSyncStatus.sync_stats.pushed_to_google || 0} to Google, 
                                Pulled {calendarSyncStatus.sync_stats.pulled_from_google || 0} from Google
                              </div>
                            )}
                          </div>
                        )}

                        <div className="flex gap-2 mt-4">
                          <button
                            onClick={() => syncCalendar('to_google')}
                            disabled={syncing}
                            className="flex-1 px-3 py-2 border border-border rounded-lg text-sm hover:bg-accent/5 disabled:opacity-50"
                          >
                            Push to Google →
                          </button>
                          <button
                            onClick={() => syncCalendar('from_google')}
                            disabled={syncing}
                            className="flex-1 px-3 py-2 border border-border rounded-lg text-sm hover:bg-accent/5 disabled:opacity-50"
                          >
                            ← Pull from Google
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-6">
                    <p className="text-secondary mb-4">
                      Connect your Google account to sync calendars, create Meet links, and access Drive files.
                    </p>
                    <button
                      onClick={() => connectGoogle('drive,calendar')}
                      disabled={connectingGoogle}
                      className="px-6 py-3 bg-primary text-white rounded-lg font-medium hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2 mx-auto"
                    >
                      {connectingGoogle ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                      ) : (
                        <svg className="w-5 h-5" viewBox="0 0 24 24">
                          <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                          <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                        </svg>
                      )}
                      Connect Google Account
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* Other Integrations */}
            <h3 className="text-lg font-semibold mt-8 mb-4">Other Integrations</h3>
            <div className="grid md:grid-cols-2 gap-4">
              {[
                { name: 'Twilio', status: 'connected', icon: Phone, description: 'VoIP & Click-to-Call' },
                { name: 'OpenAI Whisper', status: 'connected', icon: Bell, description: 'Call transcription' },
                { name: 'Resend', status: 'connected', icon: Mail, description: 'Email notifications' },
                { name: 'HubSpot', status: 'coming_soon', icon: Link2, description: 'CRM sync' },
                { name: 'Salesforce', status: 'coming_soon', icon: Link2, description: 'CRM sync' },
                { name: 'Zapier', status: 'coming_soon', icon: Link2, description: 'Workflow automation' }
              ].map((integration) => (
                <div key={integration.name} className="bg-card rounded-xl border border-border p-4 flex items-center gap-4">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                    integration.status === 'connected' ? 'bg-green-100' : 'bg-slate-100'
                  }`}>
                    <integration.icon className={`w-5 h-5 ${
                      integration.status === 'connected' ? 'text-green-600' : 'text-slate-400'
                    }`} />
                  </div>
                  <div className="flex-1">
                    <h4 className="font-medium">{integration.name}</h4>
                    <p className="text-xs text-secondary">{integration.description}</p>
                  </div>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    integration.status === 'connected' ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500'
                  }`}>
                    {integration.status === 'connected' ? 'Active' : 'Coming Soon'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* New API Key Modal */}
        {showNewKeyModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-card rounded-xl p-6 max-w-md w-full">
              {!createdKey ? (
                <>
                  <h3 className="text-xl font-semibold mb-4">Create API Key</h3>
                  
                  <div className="mb-4">
                    <label className="block text-sm font-medium mb-2">Key Name</label>
                    <input
                      type="text"
                      value={newKeyName}
                      onChange={(e) => setNewKeyName(e.target.value)}
                      placeholder="e.g., Production Server"
                      className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                  </div>

                  <div className="mb-6">
                    <label className="block text-sm font-medium mb-2">Permissions</label>
                    <div className="space-y-2">
                      {permissions.map(perm => (
                        <label key={perm.id} className="flex items-start gap-3 p-3 border border-border rounded-lg cursor-pointer hover:bg-accent/5">
                          <input
                            type="checkbox"
                            checked={newKeyPermissions.includes(perm.id)}
                            onChange={() => togglePermission(perm.id)}
                            className="mt-1"
                          />
                          <div>
                            <p className="font-medium">{perm.label}</p>
                            <p className="text-sm text-secondary">{perm.description}</p>
                          </div>
                        </label>
                      ))}
                    </div>
                  </div>

                  <div className="flex gap-3">
                    <button
                      onClick={() => setShowNewKeyModal(false)}
                      className="flex-1 py-3 border border-border rounded-lg font-medium hover:bg-accent/5"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={createApiKey}
                      disabled={loading || !newKeyName.trim()}
                      className="flex-1 py-3 bg-primary text-white rounded-lg font-medium hover:bg-primary/90 disabled:opacity-50 flex items-center justify-center gap-2"
                    >
                      {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Key className="w-5 h-5" />}
                      Create
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <div className="text-center mb-6">
                    <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                      <CheckCircle className="w-8 h-8 text-green-600" />
                    </div>
                    <h3 className="text-xl font-semibold">API Key Created!</h3>
                    <p className="text-secondary text-sm mt-1">Save this key securely - it won't be shown again</p>
                  </div>

                  <div className="bg-slate-100 rounded-lg p-4 mb-6">
                    <p className="text-xs text-secondary mb-1">Your API Key</p>
                    <div className="flex items-center gap-2">
                      <code className="flex-1 text-sm font-mono break-all">{createdKey.key}</code>
                      <button
                        onClick={() => copyToClipboard(createdKey.key)}
                        className="p-2 hover:bg-slate-200 rounded"
                      >
                        <Copy className="w-5 h-5" />
                      </button>
                    </div>
                  </div>

                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
                    <div className="flex gap-2">
                      <AlertCircle className="w-5 h-5 text-yellow-600 flex-shrink-0" />
                      <div className="text-sm text-yellow-800">
                        <p className="font-medium">Important</p>
                        <p>Store this key in a secure location. You won't be able to see it again.</p>
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={() => setShowNewKeyModal(false)}
                    className="w-full py-3 bg-primary text-white rounded-lg font-medium hover:bg-primary/90"
                  >
                    Done
                  </button>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
};

export default SettingsPage;
