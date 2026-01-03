import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Mail, Send, Clock, Users, Sparkles, Plus, Search, 
  Edit, Trash2, Copy, Eye, X, ChevronDown, ChevronRight,
  FileText, Zap, Calendar, CheckCircle, AlertCircle,
  Loader2, MailPlus, RefreshCw, Filter, Settings,
  Bot, Wand2, PlayCircle, PauseCircle, BarChart3
} from 'lucide-react';
import { toast } from 'react-toastify';
import { format, addDays, addHours } from 'date-fns';
import { motion, AnimatePresence } from 'framer-motion';
import DashboardLayout from '@/components/DashboardLayout';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const AIEmailPage = () => {
  const [activeTab, setActiveTab] = useState('compose');
  const [templates, setTemplates] = useState([]);
  const [campaigns, setCampaigns] = useState([]);
  const [scheduledEmails, setScheduledEmails] = useState([]);
  const [leads, setLeads] = useState([]);
  const [selectedLeads, setSelectedLeads] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showTemplateModal, setShowTemplateModal] = useState(false);
  const [showPreviewModal, setShowPreviewModal] = useState(null);
  const [generating, setGenerating] = useState(false);
  
  // Email compose state
  const [emailData, setEmailData] = useState({
    subject: '',
    body: '',
    template_id: null,
    schedule_time: null,
    ai_personalize: true,
    follow_up_enabled: false,
    follow_up_days: 3,
    follow_up_count: 2
  });

  // Template state
  const [templateData, setTemplateData] = useState({
    name: '',
    subject: '',
    body: '',
    category: 'outreach',
    variables: []
  });

  // AI generation prompt
  const [aiPrompt, setAiPrompt] = useState('');

  useEffect(() => {
    fetchData();
  }, []);

  const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return { headers: { Authorization: `Bearer ${token}` } };
  };

  const fetchData = async () => {
    setLoading(true);
    try {
      const [templatesRes, leadsRes, campaignsRes, scheduledRes] = await Promise.all([
        axios.get(`${API_URL}/api/email/templates`, getAuthHeaders()),
        axios.get(`${API_URL}/api/leads`, getAuthHeaders()),
        axios.get(`${API_URL}/api/email/campaigns`, getAuthHeaders()),
        axios.get(`${API_URL}/api/email/scheduled`, getAuthHeaders())
      ]);
      setTemplates(templatesRes.data);
      setLeads(leadsRes.data);
      setCampaigns(campaignsRes.data);
      setScheduledEmails(scheduledRes.data);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  };

  const generateAIEmail = async () => {
    if (!aiPrompt.trim()) {
      toast.error('Please enter a prompt for the AI');
      return;
    }

    setGenerating(true);
    try {
      const response = await axios.post(`${API_URL}/api/email/generate`, {
        prompt: aiPrompt,
        context: selectedLeads.length > 0 ? 'bulk_outreach' : 'single_email',
        lead_count: selectedLeads.length
      }, getAuthHeaders());

      setEmailData(prev => ({
        ...prev,
        subject: response.data.subject,
        body: response.data.body
      }));
      toast.success('AI generated your email!');
    } catch (error) {
      toast.error('Failed to generate email');
    } finally {
      setGenerating(false);
    }
  };

  const sendBulkEmail = async () => {
    if (selectedLeads.length === 0) {
      toast.error('Please select at least one recipient');
      return;
    }
    if (!emailData.subject || !emailData.body) {
      toast.error('Please fill in subject and body');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(`${API_URL}/api/email/send-bulk`, {
        lead_ids: selectedLeads,
        subject: emailData.subject,
        body: emailData.body,
        ai_personalize: emailData.ai_personalize,
        schedule_time: emailData.schedule_time,
        follow_up: emailData.follow_up_enabled ? {
          days: emailData.follow_up_days,
          count: emailData.follow_up_count
        } : null
      }, getAuthHeaders());

      toast.success(`${response.data.sent_count} emails ${emailData.schedule_time ? 'scheduled' : 'sent'} successfully!`);
      setSelectedLeads([]);
      setEmailData({
        subject: '',
        body: '',
        template_id: null,
        schedule_time: null,
        ai_personalize: true,
        follow_up_enabled: false,
        follow_up_days: 3,
        follow_up_count: 2
      });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send emails');
    } finally {
      setLoading(false);
    }
  };

  const saveTemplate = async () => {
    if (!templateData.name || !templateData.subject || !templateData.body) {
      toast.error('Please fill in all template fields');
      return;
    }

    try {
      await axios.post(`${API_URL}/api/email/templates`, templateData, getAuthHeaders());
      toast.success('Template saved!');
      setShowTemplateModal(false);
      setTemplateData({ name: '', subject: '', body: '', category: 'outreach', variables: [] });
      fetchData();
    } catch (error) {
      toast.error('Failed to save template');
    }
  };

  const deleteTemplate = async (templateId) => {
    if (!window.confirm('Delete this template?')) return;
    
    try {
      await axios.delete(`${API_URL}/api/email/templates/${templateId}`, getAuthHeaders());
      toast.success('Template deleted');
      fetchData();
    } catch (error) {
      toast.error('Failed to delete template');
    }
  };

  const applyTemplate = (template) => {
    setEmailData(prev => ({
      ...prev,
      subject: template.subject,
      body: template.body,
      template_id: template.id
    }));
    setActiveTab('compose');
    toast.success(`Template "${template.name}" loaded`);
  };

  const toggleLeadSelection = (leadId) => {
    setSelectedLeads(prev => 
      prev.includes(leadId) 
        ? prev.filter(id => id !== leadId)
        : [...prev, leadId]
    );
  };

  const selectAllLeads = () => {
    if (selectedLeads.length === leads.length) {
      setSelectedLeads([]);
    } else {
      setSelectedLeads(leads.map(l => l.id));
    }
  };

  const cancelScheduledEmail = async (emailId) => {
    try {
      await axios.delete(`${API_URL}/api/email/scheduled/${emailId}`, getAuthHeaders());
      toast.success('Scheduled email cancelled');
      fetchData();
    } catch (error) {
      toast.error('Failed to cancel email');
    }
  };

  const templateCategories = [
    { id: 'outreach', label: 'Cold Outreach', icon: MailPlus },
    { id: 'follow_up', label: 'Follow Up', icon: RefreshCw },
    { id: 'meeting', label: 'Meeting Request', icon: Calendar },
    { id: 'proposal', label: 'Proposal', icon: FileText },
    { id: 'nurture', label: 'Lead Nurture', icon: Sparkles }
  ];

  const aiSuggestions = [
    'Write a cold outreach email for a SaaS product',
    'Create a follow-up email after no response',
    'Draft a meeting request email',
    'Write a thank you email after a demo',
    'Create an email to re-engage cold leads'
  ];

  return (
    <DashboardLayout>
      <div data-testid="ai-email-page">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-4xl font-bold text-foreground mb-2">AI Email Automation</h1>
            <p className="text-secondary">Create, automate, and send personalized emails at scale</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowTemplateModal(true)}
              className="px-4 py-2 border border-border rounded-lg hover:bg-slate-50 flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              New Template
            </button>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-white p-4 rounded-xl border border-border">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                <Mail className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{campaigns.reduce((acc, c) => acc + (c.sent_count || 0), 0)}</p>
                <p className="text-sm text-secondary">Emails Sent</p>
              </div>
            </div>
          </div>
          <div className="bg-white p-4 rounded-xl border border-border">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                <CheckCircle className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{campaigns.reduce((acc, c) => acc + (c.opened_count || 0), 0)}</p>
                <p className="text-sm text-secondary">Opened</p>
              </div>
            </div>
          </div>
          <div className="bg-white p-4 rounded-xl border border-border">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                <Clock className="w-5 h-5 text-purple-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{scheduledEmails.length}</p>
                <p className="text-sm text-secondary">Scheduled</p>
              </div>
            </div>
          </div>
          <div className="bg-white p-4 rounded-xl border border-border">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
                <FileText className="w-5 h-5 text-orange-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{templates.length}</p>
                <p className="text-sm text-secondary">Templates</p>
              </div>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 border-b border-border">
          {[
            { id: 'compose', label: 'Compose & Send', icon: Send },
            { id: 'templates', label: 'Templates', icon: FileText },
            { id: 'scheduled', label: 'Scheduled', icon: Clock },
            { id: 'campaigns', label: 'Campaigns', icon: BarChart3 }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-3 flex items-center gap-2 font-medium transition-colors border-b-2 -mb-[2px] ${
                activeTab === tab.id 
                  ? 'text-primary border-primary' 
                  : 'text-secondary border-transparent hover:text-foreground'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Compose Tab */}
        {activeTab === 'compose' && (
          <div className="grid lg:grid-cols-3 gap-6">
            {/* Left: Recipients */}
            <div className="bg-white rounded-xl border border-border overflow-hidden">
              <div className="p-4 border-b border-border">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold flex items-center gap-2">
                    <Users className="w-4 h-4" />
                    Recipients ({selectedLeads.length})
                  </h3>
                  <button
                    onClick={selectAllLeads}
                    className="text-sm text-primary hover:underline"
                  >
                    {selectedLeads.length === leads.length ? 'Deselect All' : 'Select All'}
                  </button>
                </div>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <input
                    type="text"
                    placeholder="Search leads..."
                    className="w-full pl-9 pr-3 py-2 border border-border rounded-lg text-sm"
                  />
                </div>
              </div>
              <div className="max-h-[400px] overflow-y-auto divide-y divide-border">
                {leads.map(lead => (
                  <label
                    key={lead.id}
                    className={`flex items-center gap-3 p-3 cursor-pointer hover:bg-slate-50 transition-colors ${
                      selectedLeads.includes(lead.id) ? 'bg-primary/5' : ''
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={selectedLeads.includes(lead.id)}
                      onChange={() => toggleLeadSelection(lead.id)}
                      className="w-4 h-4 rounded border-slate-300"
                    />
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm truncate">{lead.first_name} {lead.last_name}</p>
                      <p className="text-xs text-secondary truncate">{lead.email}</p>
                    </div>
                    <span className="text-xs text-secondary">{lead.company}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Center: Email Composer */}
            <div className="lg:col-span-2 space-y-4">
              {/* AI Generation */}
              <div className="bg-gradient-to-r from-purple-50 to-blue-50 rounded-xl p-4 border border-purple-100">
                <h3 className="font-semibold mb-3 flex items-center gap-2">
                  <Wand2 className="w-5 h-5 text-purple-600" />
                  AI Email Generator
                </h3>
                <div className="flex gap-2 mb-3">
                  <input
                    type="text"
                    value={aiPrompt}
                    onChange={(e) => setAiPrompt(e.target.value)}
                    placeholder="Describe the email you want to write..."
                    className="flex-1 px-4 py-2 border border-purple-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                  />
                  <button
                    onClick={generateAIEmail}
                    disabled={generating}
                    className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 flex items-center gap-2"
                  >
                    {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                    Generate
                  </button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {aiSuggestions.map((suggestion, idx) => (
                    <button
                      key={idx}
                      onClick={() => setAiPrompt(suggestion)}
                      className="px-3 py-1 bg-white border border-purple-200 rounded-full text-xs hover:bg-purple-50 transition-colors"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>

              {/* Email Form */}
              <div className="bg-white rounded-xl border border-border p-4 space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Subject Line</label>
                  <input
                    type="text"
                    value={emailData.subject}
                    onChange={(e) => setEmailData({ ...emailData, subject: e.target.value })}
                    placeholder="Enter email subject..."
                    className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Email Body</label>
                  <textarea
                    value={emailData.body}
                    onChange={(e) => setEmailData({ ...emailData, body: e.target.value })}
                    placeholder="Write your email content here... Use {{first_name}}, {{company}}, etc. for personalization"
                    rows={10}
                    className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary resize-none"
                  />
                  <p className="text-xs text-secondary mt-1">
                    Available variables: {"{{first_name}}, {{last_name}}, {{company}}, {{title}}"}
                  </p>
                </div>

                {/* Options */}
                <div className="grid grid-cols-2 gap-4 pt-4 border-t border-border">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={emailData.ai_personalize}
                      onChange={(e) => setEmailData({ ...emailData, ai_personalize: e.target.checked })}
                      className="w-4 h-4 rounded"
                    />
                    <span className="text-sm">AI Personalization</span>
                    <Bot className="w-4 h-4 text-purple-600" />
                  </label>

                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={emailData.follow_up_enabled}
                      onChange={(e) => setEmailData({ ...emailData, follow_up_enabled: e.target.checked })}
                      className="w-4 h-4 rounded"
                    />
                    <span className="text-sm">Auto Follow-ups</span>
                    <RefreshCw className="w-4 h-4 text-blue-600" />
                  </label>
                </div>

                {emailData.follow_up_enabled && (
                  <div className="grid grid-cols-2 gap-4 p-3 bg-blue-50 rounded-lg">
                    <div>
                      <label className="block text-xs font-medium mb-1">Days between follow-ups</label>
                      <input
                        type="number"
                        min="1"
                        max="14"
                        value={emailData.follow_up_days}
                        onChange={(e) => setEmailData({ ...emailData, follow_up_days: parseInt(e.target.value) })}
                        className="w-full px-3 py-1.5 border border-border rounded-lg text-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium mb-1">Number of follow-ups</label>
                      <input
                        type="number"
                        min="1"
                        max="5"
                        value={emailData.follow_up_count}
                        onChange={(e) => setEmailData({ ...emailData, follow_up_count: parseInt(e.target.value) })}
                        className="w-full px-3 py-1.5 border border-border rounded-lg text-sm"
                      />
                    </div>
                  </div>
                )}

                {/* Schedule */}
                <div className="pt-4 border-t border-border">
                  <label className="block text-sm font-medium mb-2">Schedule (optional)</label>
                  <input
                    type="datetime-local"
                    value={emailData.schedule_time || ''}
                    onChange={(e) => setEmailData({ ...emailData, schedule_time: e.target.value })}
                    className="px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>

                {/* Actions */}
                <div className="flex gap-3 pt-4">
                  <button
                    onClick={sendBulkEmail}
                    disabled={loading || selectedLeads.length === 0}
                    className="flex-1 py-3 bg-primary text-white rounded-xl font-medium hover:bg-primary/90 disabled:opacity-50 flex items-center justify-center gap-2"
                  >
                    {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
                    {emailData.schedule_time ? 'Schedule' : 'Send'} to {selectedLeads.length} Recipients
                  </button>
                  <button
                    onClick={() => setShowPreviewModal(emailData)}
                    disabled={!emailData.subject || !emailData.body}
                    className="px-4 py-3 border border-border rounded-xl hover:bg-slate-50 flex items-center gap-2"
                  >
                    <Eye className="w-5 h-5" />
                    Preview
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Templates Tab */}
        {activeTab === 'templates' && (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {templates.length === 0 ? (
              <div className="col-span-full text-center py-12 bg-white rounded-xl border border-border">
                <FileText className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                <p className="text-secondary mb-4">No templates yet</p>
                <button
                  onClick={() => setShowTemplateModal(true)}
                  className="px-4 py-2 bg-primary text-white rounded-lg"
                >
                  Create Your First Template
                </button>
              </div>
            ) : (
              templates.map(template => (
                <motion.div
                  key={template.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="bg-white rounded-xl border border-border overflow-hidden hover:shadow-md transition-shadow"
                >
                  <div className="p-4">
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <h3 className="font-semibold">{template.name}</h3>
                        <span className="text-xs px-2 py-0.5 bg-slate-100 rounded-full capitalize">
                          {template.category?.replace('_', ' ')}
                        </span>
                      </div>
                      <div className="flex gap-1">
                        <button
                          onClick={() => applyTemplate(template)}
                          className="p-1.5 hover:bg-slate-100 rounded-lg"
                          title="Use Template"
                        >
                          <Copy className="w-4 h-4 text-slate-600" />
                        </button>
                        <button
                          onClick={() => deleteTemplate(template.id)}
                          className="p-1.5 hover:bg-red-50 rounded-lg"
                          title="Delete"
                        >
                          <Trash2 className="w-4 h-4 text-red-500" />
                        </button>
                      </div>
                    </div>
                    <p className="text-sm font-medium text-slate-700 mb-1">{template.subject}</p>
                    <p className="text-xs text-secondary line-clamp-3">{template.body}</p>
                  </div>
                  <div className="px-4 py-2 bg-slate-50 border-t border-border">
                    <button
                      onClick={() => useTemplate(template)}
                      className="w-full py-1.5 text-sm text-primary hover:bg-primary/10 rounded-lg transition-colors"
                    >
                      Use This Template
                    </button>
                  </div>
                </motion.div>
              ))
            )}
          </div>
        )}

        {/* Scheduled Tab */}
        {activeTab === 'scheduled' && (
          <div className="bg-white rounded-xl border border-border overflow-hidden">
            {scheduledEmails.length === 0 ? (
              <div className="text-center py-12">
                <Clock className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                <p className="text-secondary">No scheduled emails</p>
              </div>
            ) : (
              <table className="w-full">
                <thead className="bg-slate-50 border-b border-border">
                  <tr>
                    <th className="text-left px-4 py-3 text-sm font-semibold">Subject</th>
                    <th className="text-left px-4 py-3 text-sm font-semibold">Recipients</th>
                    <th className="text-left px-4 py-3 text-sm font-semibold">Scheduled For</th>
                    <th className="text-left px-4 py-3 text-sm font-semibold">Status</th>
                    <th className="text-right px-4 py-3 text-sm font-semibold">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {scheduledEmails.map(email => (
                    <tr key={email.id} className="hover:bg-slate-50">
                      <td className="px-4 py-3">
                        <p className="font-medium">{email.subject}</p>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-sm">{email.recipient_count} leads</span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-sm">{format(new Date(email.scheduled_time), 'MMM d, yyyy h:mm a')}</span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          email.status === 'pending' ? 'bg-yellow-100 text-yellow-700' :
                          email.status === 'sent' ? 'bg-green-100 text-green-700' :
                          'bg-red-100 text-red-700'
                        }`}>
                          {email.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        {email.status === 'pending' && (
                          <button
                            onClick={() => cancelScheduledEmail(email.id)}
                            className="text-red-500 hover:underline text-sm"
                          >
                            Cancel
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {/* Campaigns Tab */}
        {activeTab === 'campaigns' && (
          <div className="bg-white rounded-xl border border-border overflow-hidden">
            {campaigns.length === 0 ? (
              <div className="text-center py-12">
                <BarChart3 className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                <p className="text-secondary">No campaigns yet. Send your first bulk email to create a campaign.</p>
              </div>
            ) : (
              <table className="w-full">
                <thead className="bg-slate-50 border-b border-border">
                  <tr>
                    <th className="text-left px-4 py-3 text-sm font-semibold">Campaign</th>
                    <th className="text-left px-4 py-3 text-sm font-semibold">Sent</th>
                    <th className="text-left px-4 py-3 text-sm font-semibold">Opened</th>
                    <th className="text-left px-4 py-3 text-sm font-semibold">Clicked</th>
                    <th className="text-left px-4 py-3 text-sm font-semibold">Replied</th>
                    <th className="text-left px-4 py-3 text-sm font-semibold">Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {campaigns.map(campaign => (
                    <tr key={campaign.id} className="hover:bg-slate-50">
                      <td className="px-4 py-3">
                        <p className="font-medium">{campaign.subject}</p>
                      </td>
                      <td className="px-4 py-3 text-sm">{campaign.sent_count}</td>
                      <td className="px-4 py-3 text-sm">
                        {campaign.opened_count} ({Math.round((campaign.opened_count / campaign.sent_count) * 100)}%)
                      </td>
                      <td className="px-4 py-3 text-sm">
                        {campaign.clicked_count} ({Math.round((campaign.clicked_count / campaign.sent_count) * 100)}%)
                      </td>
                      <td className="px-4 py-3 text-sm">
                        {campaign.replied_count} ({Math.round((campaign.replied_count / campaign.sent_count) * 100)}%)
                      </td>
                      <td className="px-4 py-3 text-sm">{format(new Date(campaign.created_at), 'MMM d, yyyy')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {/* Template Modal */}
        <AnimatePresence>
          {showTemplateModal && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
              onClick={(e) => e.target === e.currentTarget && setShowTemplateModal(false)}
            >
              <motion.div
                initial={{ scale: 0.95 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0.95 }}
                className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto"
              >
                <div className="p-6 border-b border-border flex items-center justify-between">
                  <h2 className="text-xl font-bold">Create Email Template</h2>
                  <button onClick={() => setShowTemplateModal(false)}>
                    <X className="w-5 h-5" />
                  </button>
                </div>
                <div className="p-6 space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium mb-1">Template Name</label>
                      <input
                        type="text"
                        value={templateData.name}
                        onChange={(e) => setTemplateData({ ...templateData, name: e.target.value })}
                        placeholder="e.g., Cold Outreach v1"
                        className="w-full px-4 py-2 border border-border rounded-lg"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">Category</label>
                      <select
                        value={templateData.category}
                        onChange={(e) => setTemplateData({ ...templateData, category: e.target.value })}
                        className="w-full px-4 py-2 border border-border rounded-lg"
                      >
                        {templateCategories.map(cat => (
                          <option key={cat.id} value={cat.id}>{cat.label}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Subject Line</label>
                    <input
                      type="text"
                      value={templateData.subject}
                      onChange={(e) => setTemplateData({ ...templateData, subject: e.target.value })}
                      placeholder="Email subject..."
                      className="w-full px-4 py-2 border border-border rounded-lg"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Email Body</label>
                    <textarea
                      value={templateData.body}
                      onChange={(e) => setTemplateData({ ...templateData, body: e.target.value })}
                      placeholder="Write your template... Use {{first_name}}, {{company}}, etc."
                      rows={8}
                      className="w-full px-4 py-2 border border-border rounded-lg resize-none"
                    />
                  </div>
                  <div className="flex gap-3 pt-4">
                    <button
                      onClick={() => setShowTemplateModal(false)}
                      className="flex-1 py-2 border border-border rounded-lg hover:bg-slate-50"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={saveTemplate}
                      className="flex-1 py-2 bg-primary text-white rounded-lg hover:bg-primary/90"
                    >
                      Save Template
                    </button>
                  </div>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Preview Modal */}
        <AnimatePresence>
          {showPreviewModal && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
              onClick={(e) => e.target === e.currentTarget && setShowPreviewModal(null)}
            >
              <motion.div
                initial={{ scale: 0.95 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0.95 }}
                className="bg-white rounded-xl shadow-xl w-full max-w-2xl"
              >
                <div className="p-6 border-b border-border flex items-center justify-between">
                  <h2 className="text-xl font-bold">Email Preview</h2>
                  <button onClick={() => setShowPreviewModal(null)}>
                    <X className="w-5 h-5" />
                  </button>
                </div>
                <div className="p-6">
                  <div className="mb-4">
                    <p className="text-sm text-secondary">Subject:</p>
                    <p className="font-semibold text-lg">{showPreviewModal.subject}</p>
                  </div>
                  <div className="bg-slate-50 rounded-lg p-4">
                    <p className="whitespace-pre-wrap">{showPreviewModal.body}</p>
                  </div>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </DashboardLayout>
  );
};

export default AIEmailPage;
