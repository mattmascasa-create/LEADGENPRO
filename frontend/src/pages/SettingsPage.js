import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Key, Plus, Copy, Trash2, Eye, EyeOff, Shield, 
  Settings, Phone, Bell, Link2, Code, CheckCircle,
  AlertCircle, Loader2, RefreshCw, ExternalLink,
  HardDrive, Calendar, Video, Mail, User as UserIcon
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
  const [profileForm, setProfileForm] = useState({
    full_name: '',
    phone: '',
    company: '',
    department: ''
  });
  const [savingProfile, setSavingProfile] = useState(false);

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
          <div className="grid md:grid-cols-2 gap-6">
            {[
              { name: 'Twilio', status: 'connected', icon: Phone, description: 'VoIP & Click-to-Call' },
              { name: 'OpenAI Whisper', status: 'connected', icon: Bell, description: 'Call transcription' },
              { name: 'Resend', status: 'connected', icon: Bell, description: 'Email notifications' },
              { name: 'Google Drive', status: 'not_configured', icon: Link2, description: 'Content storage' },
              { name: 'HubSpot', status: 'coming_soon', icon: Link2, description: 'CRM sync' },
              { name: 'Salesforce', status: 'coming_soon', icon: Link2, description: 'CRM sync' }
            ].map((integration) => (
              <div key={integration.name} className="bg-card rounded-xl border border-border p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                      integration.status === 'connected' ? 'bg-green-100' :
                      integration.status === 'not_configured' ? 'bg-yellow-100' :
                      'bg-slate-100'
                    }`}>
                      <integration.icon className={`w-6 h-6 ${
                        integration.status === 'connected' ? 'text-green-600' :
                        integration.status === 'not_configured' ? 'text-yellow-600' :
                        'text-slate-400'
                      }`} />
                    </div>
                    <div>
                      <h3 className="font-semibold">{integration.name}</h3>
                      <p className="text-sm text-secondary">{integration.description}</p>
                    </div>
                  </div>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    integration.status === 'connected' ? 'bg-green-100 text-green-700' :
                    integration.status === 'not_configured' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-slate-100 text-slate-500'
                  }`}>
                    {integration.status === 'connected' ? 'Connected' :
                     integration.status === 'not_configured' ? 'Not Configured' :
                     'Coming Soon'}
                  </span>
                </div>
                {integration.status !== 'coming_soon' && (
                  <button className="w-full py-2 border border-border rounded-lg text-sm font-medium hover:bg-accent/5">
                    {integration.status === 'connected' ? 'Configure' : 'Set Up'}
                  </button>
                )}
              </div>
            ))}
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
