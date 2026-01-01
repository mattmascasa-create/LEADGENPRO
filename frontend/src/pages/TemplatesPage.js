import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import { Plus, FileText, Search, Mail, MessageSquare, Copy, Edit, Trash2, Sparkles } from 'lucide-react';
import { toast } from 'react-toastify';
import DashboardLayout from '@/components/DashboardLayout';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const TemplatesPage = () => {
  const [templates, setTemplates] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [formData, setFormData] = useState({
    name: '',
    subject: '',
    body: '',
    category: 'general'
  });

  const categories = [
    { id: 'all', label: 'All Templates', icon: FileText },
    { id: 'cold_outreach', label: 'Cold Outreach', icon: Mail },
    { id: 'follow_up', label: 'Follow-up', icon: MessageSquare },
    { id: 'meeting_request', label: 'Meeting Request', icon: FileText },
    { id: 'proposal', label: 'Proposal', icon: FileText }
  ];

  useEffect(() => {
    fetchTemplates();
  }, []);

  const fetchTemplates = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/templates`);
      setTemplates(response.data);
    } catch (error) {
      toast.error('Failed to load templates');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API_URL}/api/templates`, formData);
      toast.success('Template created successfully!');
      setShowForm(false);
      setFormData({ name: '', subject: '', body: '', category: 'general' });
      fetchTemplates();
    } catch (error) {
      toast.error('Failed to create template');
    }
  };

  const copyTemplate = (template) => {
    navigator.clipboard.writeText(template.body);
    toast.success('Template copied to clipboard!');
  };

  const filteredTemplates = templates.filter(template => {
    const matchesSearch = template.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         template.subject.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = selectedCategory === 'all' || template.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  return (
    <DashboardLayout>
      <div>
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-4xl font-bold text-foreground mb-2">Templates Library</h1>
            <p className="text-secondary">Save time with reusable email and message templates</p>
          </div>
          <button
            onClick={() => setShowForm(!showForm)}
            className="px-6 py-3 bg-primary text-white rounded-lg font-semibold hover:bg-primary/90 transition-all duration-200 flex items-center gap-2"
          >
            <Plus className="w-5 h-5" />
            Create Template
          </button>
        </div>

        {/* Search and Filter */}
        <div className="bg-white p-6 rounded-xl border border-border mb-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-secondary" />
                <input
                  type="text"
                  placeholder="Search templates..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-12 pr-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
            </div>
            <div className="flex gap-2 overflow-x-auto pb-2">
              {categories.map((category) => {
                const Icon = category.icon;
                return (
                  <button
                    key={category.id}
                    onClick={() => setSelectedCategory(category.id)}
                    className={`px-4 py-2 rounded-lg font-medium whitespace-nowrap transition-all duration-200 flex items-center gap-2 ${
                      selectedCategory === category.id
                        ? 'bg-primary text-white'
                        : 'border border-border hover:bg-slate-50'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    {category.label}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Create Form */}
        {showForm && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white p-6 rounded-xl border border-border mb-6"
          >
            <h3 className="text-xl font-semibold text-foreground mb-4">Create New Template</h3>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid md:grid-cols-2 gap-4">
                <input
                  type="text"
                  placeholder="Template Name"
                  value={formData.name}
                  onChange={(e) => setFormData({...formData, name: e.target.value})}
                  required
                  className="px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                />
                <select
                  value={formData.category}
                  onChange={(e) => setFormData({...formData, category: e.target.value})}
                  className="px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="general">General</option>
                  <option value="cold_outreach">Cold Outreach</option>
                  <option value="follow_up">Follow-up</option>
                  <option value="meeting_request">Meeting Request</option>
                  <option value="proposal">Proposal</option>
                </select>
              </div>
              <input
                type="text"
                placeholder="Email Subject"
                value={formData.subject}
                onChange={(e) => setFormData({...formData, subject: e.target.value})}
                required
                className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <textarea
                placeholder="Email Body (use {{first_name}}, {{company}} for personalization)"
                value={formData.body}
                onChange={(e) => setFormData({...formData, body: e.target.value})}
                required
                rows={8}
                className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary resize-none font-mono text-sm"
              />
              <div className="flex gap-3">
                <button type="submit" className="flex-1 py-3 bg-primary text-white rounded-lg font-semibold hover:bg-primary/90 transition-all">
                  Create Template
                </button>
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="px-6 py-3 border-2 border-border rounded-lg font-semibold hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </form>
          </motion.div>
        )}

        {/* Templates Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredTemplates.map((template, index) => (
            <motion.div
              key={template.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className="bg-white p-6 rounded-xl border border-border hover:border-primary transition-all duration-200 flex flex-col"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <h4 className="text-lg font-bold text-foreground mb-1">{template.name}</h4>
                  <span className="inline-block px-2 py-1 bg-slate-100 text-slate-600 text-xs font-medium rounded">
                    {template.category.replace('_', ' ')}
                  </span>
                </div>
              </div>

              <div className="mb-4">
                <p className="text-sm font-semibold text-foreground mb-2">Subject:</p>
                <p className="text-sm text-secondary">{template.subject}</p>
              </div>

              <div className="flex-1 mb-4">
                <p className="text-sm font-semibold text-foreground mb-2">Body:</p>
                <div className="bg-slate-50 p-3 rounded-lg text-xs text-secondary font-mono max-h-32 overflow-y-auto">
                  {template.body}
                </div>
              </div>

              <div className="flex gap-2 pt-4 border-t border-border">
                <button
                  onClick={() => copyTemplate(template)}
                  className="flex-1 px-3 py-2 border border-border rounded-lg text-sm font-medium hover:bg-slate-50 transition-colors flex items-center justify-center gap-2"
                >
                  <Copy className="w-4 h-4" />
                  Copy
                </button>
                <button className="px-3 py-2 border border-border rounded-lg text-sm font-medium hover:bg-slate-50 transition-colors">
                  <Edit className="w-4 h-4" />
                </button>
                <button className="px-3 py-2 border border-destructive text-destructive rounded-lg text-sm font-medium hover:bg-destructive/10 transition-colors">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </motion.div>
          ))}

          {filteredTemplates.length === 0 && (
            <div className="col-span-full text-center py-16">
              <FileText className="w-16 h-16 text-secondary mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-foreground mb-2">No templates found</h3>
              <p className="text-secondary mb-6">
                {templates.length === 0 ? 'Create your first template to get started' : 'Try a different search or filter'}
              </p>
              {templates.length === 0 && (
                <button
                  onClick={() => setShowForm(true)}
                  className="px-6 py-3 bg-primary text-white rounded-lg font-semibold hover:bg-primary/90 transition-all duration-200 inline-flex items-center gap-2"
                >
                  <Plus className="w-5 h-5" />
                  Create Your First Template
                </button>
              )}
            </div>
          )}
        </div>

        {/* AI Template Suggestion */}
        {templates.length > 0 && (
          <div className="mt-8 ai-card p-6 rounded-xl">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-accent/10 rounded-lg flex items-center justify-center flex-shrink-0">
                <Sparkles className="w-6 h-6 text-accent" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-foreground mb-2">AI Template Generator</h3>
                <p className="text-sm text-secondary mb-4">
                  Let AI help you create personalized email templates based on your best performers
                </p>
                <button className="px-4 py-2 bg-accent text-white rounded-lg font-medium hover:bg-accent/90 transition-all duration-200">
                  Generate Template with AI
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
};

export default TemplatesPage;