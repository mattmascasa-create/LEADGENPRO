import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import { 
  Link2, Unlink, RefreshCw, CheckCircle2, XCircle, 
  ExternalLink, Settings, Database, ArrowRight, Loader2,
  Building2, Cloud, Zap, Shield
} from 'lucide-react';
import { toast } from 'react-toastify';
import DashboardLayout from '@/components/DashboardLayout';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// HubSpot icon
const HubSpotIcon = () => (
  <svg className="w-8 h-8" viewBox="0 0 24 24" fill="none">
    <path d="M18.164 7.93V5.084a2.198 2.198 0 001.267-1.984 2.21 2.21 0 00-4.42 0c0 .867.503 1.615 1.233 1.975v2.855a5.52 5.52 0 00-2.466 1.191l-6.09-4.74a2.623 2.623 0 00.076-.596 2.627 2.627 0 00-5.254 0 2.627 2.627 0 002.627 2.627c.535 0 1.03-.162 1.445-.439l5.959 4.637a5.525 5.525 0 00-.198 1.443c0 .536.077 1.054.22 1.545l-2.46 1.13a2.04 2.04 0 00-1.139-.348 2.057 2.057 0 000 4.114 2.057 2.057 0 002.057-2.057c0-.164-.02-.324-.057-.477l2.365-1.086a5.538 5.538 0 109.105-5.744 5.499 5.499 0 00-2.27-1.204z" fill="#FF7A59"/>
  </svg>
);

// Salesforce icon
const SalesforceIcon = () => (
  <svg className="w-8 h-8" viewBox="0 0 24 24" fill="none">
    <path d="M10.006 5.415a4.195 4.195 0 013.045-1.306c1.56 0 2.954.856 3.68 2.143a5.05 5.05 0 012.14-.478c2.79 0 5.052 2.262 5.052 5.052 0 2.79-2.262 5.052-5.052 5.052-.47 0-.924-.064-1.357-.185a4.16 4.16 0 01-3.498 1.903 4.15 4.15 0 01-2.016-.52 4.79 4.79 0 01-4.327 2.74c-2.65 0-4.796-2.147-4.796-4.796 0-.372.042-.734.122-1.082A4.093 4.093 0 011 10.164c0-2.26 1.833-4.094 4.094-4.094.69 0 1.34.171 1.91.473a4.201 4.201 0 013.002-1.128z" fill="#00A1E0"/>
  </svg>
);

// Zoho icon
const ZohoIcon = () => (
  <svg className="w-8 h-8" viewBox="0 0 24 24" fill="none">
    <rect width="24" height="24" rx="4" fill="#C8202B"/>
    <text x="12" y="16" textAnchor="middle" fill="white" fontSize="8" fontWeight="bold">Z</text>
  </svg>
);

// Pipedrive icon
const PipedriveIcon = () => (
  <svg className="w-8 h-8" viewBox="0 0 24 24" fill="none">
    <circle cx="12" cy="12" r="10" fill="#017737"/>
    <path d="M8 12h8M12 8v8" stroke="white" strokeWidth="2" strokeLinecap="round"/>
  </svg>
);

const CRMIntegrationsPage = () => {
  const [integrations, setIntegrations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [connectingProvider, setConnectingProvider] = useState(null);

  const crmProviders = [
    {
      id: 'hubspot',
      name: 'HubSpot',
      icon: HubSpotIcon,
      description: 'Sync contacts, companies, and deals with HubSpot CRM',
      features: ['Contact Sync', 'Deal Pipeline', 'Activity Logging', 'Email Tracking'],
      color: 'from-orange-500 to-red-500',
      bgColor: 'bg-orange-50',
      borderColor: 'border-orange-200',
      status: 'coming_soon'
    },
    {
      id: 'salesforce',
      name: 'Salesforce',
      icon: SalesforceIcon,
      description: 'Connect with Salesforce for enterprise-grade CRM integration',
      features: ['Lead Sync', 'Opportunity Tracking', 'Custom Objects', 'Reports'],
      color: 'from-blue-500 to-cyan-500',
      bgColor: 'bg-blue-50',
      borderColor: 'border-blue-200',
      status: 'coming_soon'
    },
    {
      id: 'zoho',
      name: 'Zoho CRM',
      icon: ZohoIcon,
      description: 'Integrate with Zoho CRM for unified sales management',
      features: ['Contact Management', 'Deal Tracking', 'Workflow Automation', 'Analytics'],
      color: 'from-red-500 to-rose-500',
      bgColor: 'bg-red-50',
      borderColor: 'border-red-200',
      status: 'coming_soon'
    },
    {
      id: 'pipedrive',
      name: 'Pipedrive',
      icon: PipedriveIcon,
      description: 'Sync your sales pipeline with Pipedrive',
      features: ['Pipeline Sync', 'Activity Tracking', 'Deal Management', 'Reporting'],
      color: 'from-green-500 to-emerald-500',
      bgColor: 'bg-green-50',
      borderColor: 'border-green-200',
      status: 'coming_soon'
    }
  ];

  useEffect(() => {
    fetchIntegrations();
  }, []);

  const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return { headers: { Authorization: `Bearer ${token}` } };
  };

  const fetchIntegrations = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/integrations/crm`, getAuthHeaders());
      setIntegrations(response.data);
    } catch (error) {
      console.error('Failed to fetch integrations:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleConnect = async (provider) => {
    setConnectingProvider(provider.id);
    
    // For now, show coming soon message
    setTimeout(() => {
      toast.info(`${provider.name} integration coming soon! We'll notify you when it's available.`);
      setConnectingProvider(null);
    }, 1500);
  };

  const handleDisconnect = async (provider) => {
    try {
      await axios.delete(`${API_URL}/api/integrations/crm/${provider.id}`, getAuthHeaders());
      toast.success(`${provider.name} disconnected successfully`);
      fetchIntegrations();
    } catch (error) {
      toast.error('Failed to disconnect integration');
    }
  };

  const getIntegrationStatus = (providerId) => {
    const integration = integrations.find(i => i.provider === providerId);
    return integration?.status || 'disconnected';
  };

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 text-primary animate-spin" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-foreground mb-2">CRM Integrations</h1>
          <p className="text-secondary">Connect your favorite CRM platforms to sync leads, contacts, and deals</p>
        </div>

        {/* Integration Benefits */}
        <div className="grid md:grid-cols-4 gap-4 mb-8">
          {[
            { icon: Database, title: 'Sync Data', desc: 'Two-way sync with your CRM' },
            { icon: Zap, title: 'Automate', desc: 'Automated workflows' },
            { icon: Shield, title: 'Secure', desc: 'Enterprise-grade security' },
            { icon: Cloud, title: 'Real-time', desc: 'Instant updates' }
          ].map((benefit, idx) => (
            <div key={idx} className="bg-white p-4 rounded-xl border border-border flex items-center gap-3">
              <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center">
                <benefit.icon className="w-5 h-5 text-primary" />
              </div>
              <div>
                <p className="font-medium text-foreground">{benefit.title}</p>
                <p className="text-sm text-secondary">{benefit.desc}</p>
              </div>
            </div>
          ))}
        </div>

        {/* CRM Provider Cards */}
        <div className="grid md:grid-cols-2 gap-6">
          {crmProviders.map((provider, index) => {
            const Icon = provider.icon;
            const status = getIntegrationStatus(provider.id);
            const isConnected = status === 'connected';
            const isConnecting = connectingProvider === provider.id;

            return (
              <motion.div
                key={provider.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className={`bg-white rounded-xl border ${provider.borderColor} overflow-hidden hover:shadow-lg transition-all`}
              >
                {/* Card Header */}
                <div className={`${provider.bgColor} p-6 border-b ${provider.borderColor}`}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <Icon />
                      <div>
                        <h3 className="text-xl font-bold text-foreground">{provider.name}</h3>
                        <p className="text-sm text-secondary">{provider.description}</p>
                      </div>
                    </div>
                    {isConnected ? (
                      <span className="flex items-center gap-1 px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm font-medium">
                        <CheckCircle2 className="w-4 h-4" />
                        Connected
                      </span>
                    ) : provider.status === 'coming_soon' ? (
                      <span className="px-3 py-1 bg-amber-100 text-amber-700 rounded-full text-sm font-medium">
                        Coming Soon
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 px-3 py-1 bg-slate-100 text-slate-600 rounded-full text-sm font-medium">
                        <XCircle className="w-4 h-4" />
                        Not Connected
                      </span>
                    )}
                  </div>
                </div>

                {/* Card Body */}
                <div className="p-6">
                  {/* Features */}
                  <div className="mb-6">
                    <p className="text-sm font-medium text-secondary mb-3">Features</p>
                    <div className="flex flex-wrap gap-2">
                      {provider.features.map((feature, idx) => (
                        <span
                          key={idx}
                          className="px-3 py-1 bg-slate-100 text-slate-700 rounded-full text-sm"
                        >
                          {feature}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-3">
                    {isConnected ? (
                      <>
                        <button
                          onClick={() => handleDisconnect(provider)}
                          className="flex-1 py-2 border border-red-200 text-red-600 rounded-lg font-medium hover:bg-red-50 flex items-center justify-center gap-2"
                        >
                          <Unlink className="w-4 h-4" />
                          Disconnect
                        </button>
                        <button
                          className="flex-1 py-2 bg-primary text-white rounded-lg font-medium hover:bg-primary/90 flex items-center justify-center gap-2"
                        >
                          <Settings className="w-4 h-4" />
                          Configure
                        </button>
                      </>
                    ) : (
                      <button
                        onClick={() => handleConnect(provider)}
                        disabled={isConnecting}
                        className={`flex-1 py-3 bg-gradient-to-r ${provider.color} text-white rounded-lg font-medium hover:opacity-90 flex items-center justify-center gap-2 disabled:opacity-50`}
                      >
                        {isConnecting ? (
                          <>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Connecting...
                          </>
                        ) : (
                          <>
                            <Link2 className="w-4 h-4" />
                            Connect {provider.name}
                          </>
                        )}
                      </button>
                    )}
                  </div>
                </div>

                {/* Last Sync Info (if connected) */}
                {isConnected && (
                  <div className="px-6 py-3 bg-slate-50 border-t border-border flex items-center justify-between">
                    <span className="text-sm text-secondary">
                      Last synced: 5 minutes ago
                    </span>
                    <button className="text-sm text-primary hover:underline flex items-center gap-1">
                      <RefreshCw className="w-3 h-3" />
                      Sync Now
                    </button>
                  </div>
                )}
              </motion.div>
            );
          })}
        </div>

        {/* Help Section */}
        <div className="mt-8 bg-gradient-to-r from-primary/5 to-accent/5 rounded-xl p-6 border border-primary/20">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center flex-shrink-0">
              <Building2 className="w-6 h-6 text-primary" />
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-foreground mb-2">Need a Custom Integration?</h3>
              <p className="text-secondary mb-4">
                Don&apos;t see your CRM? We can build custom integrations for enterprise customers.
                Our API also allows you to build your own integrations.
              </p>
              <div className="flex gap-3">
                <a
                  href="/settings"
                  className="px-4 py-2 bg-primary text-white rounded-lg font-medium hover:bg-primary/90 inline-flex items-center gap-2"
                >
                  View API Documentation
                  <ArrowRight className="w-4 h-4" />
                </a>
                <button className="px-4 py-2 border border-border rounded-lg font-medium hover:bg-slate-50 inline-flex items-center gap-2">
                  <ExternalLink className="w-4 h-4" />
                  Contact Sales
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default CRMIntegrationsPage;
