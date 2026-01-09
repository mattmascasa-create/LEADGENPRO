import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { Plus, Search, Mail, Phone, Building, Upload, Globe, Download, Filter, ChevronRight, PhoneCall, Calendar, CheckSquare, Square, X, Users, Zap, Edit2, MapPin, FileText, Save } from 'lucide-react';
import { toast } from 'react-toastify';
import { useSearchParams } from 'react-router-dom';
import DashboardLayout from '@/components/DashboardLayout';
import CallModal from '@/components/CallModal';
import EmailModal from '@/components/EmailModal';
import MeetingModal from '@/components/MeetingModal';
import PhoneDialer from '@/components/PhoneDialer';
import { motion, AnimatePresence } from 'framer-motion';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const LeadsPage = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [leads, setLeads] = useState([]);
  const [users, setUsers] = useState([]);
  const [sequences, setSequences] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [showScraper, setShowScraper] = useState(false);
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [showSequenceModal, setShowSequenceModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingLead, setEditingLead] = useState(null);
  const [importing, setImporting] = useState(false);
  const [scraping, setScraping] = useState(false);
  const [scrapeUrl, setScrapeUrl] = useState('');
  const [showCallModal, setShowCallModal] = useState(false);
  const [showEmailModal, setShowEmailModal] = useState(false);
  const [showMeetingModal, setShowMeetingModal] = useState(false);
  const [showDialer, setShowDialer] = useState(false);
  const [selectedLeadForCall, setSelectedLeadForCall] = useState(null);
  const [selectedLeadForEmail, setSelectedLeadForEmail] = useState(null);
  const [selectedLeadForMeeting, setSelectedLeadForMeeting] = useState(null);
  const [selectedLeadForDialer, setSelectedLeadForDialer] = useState(null);
  const [selectedLeads, setSelectedLeads] = useState([]);
  const [selectMode, setSelectMode] = useState(false);
  const [selectedUserId, setSelectedUserId] = useState('');
  const [selectedSequenceId, setSelectedSequenceId] = useState('');
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    mobile: '',
    company: '',
    title: '',
    street_address: '',
    city: '',
    state: '',
    zip_code: '',
    notes: '',
    tags: []
  });

  useEffect(() => {
    fetchLeads();
    fetchUsers();
    fetchSequences();
    
    // Handle query params from copilot
    const action = searchParams.get('action');
    if (action === 'import') setShowImport(true);
    if (action === 'scrape') setShowScraper(true);
    if (action === 'create') setShowForm(true);
  }, [searchParams]);

  const fetchLeads = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/api/leads`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setLeads(response.data);
    } catch (error) {
      toast.error('Failed to load leads');
    }
  };

  const fetchUsers = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/api/users`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setUsers(response.data);
    } catch (error) {
      console.error('Failed to load users');
    }
  };

  const fetchSequences = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/api/sequences`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSequences(response.data);
    } catch (error) {
      console.error('Failed to load sequences');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API_URL}/api/leads`, formData, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Lead created successfully!');
      setShowForm(false);
      setFormData({ first_name: '', last_name: '', email: '', phone: '', mobile: '', company: '', title: '', street_address: '', city: '', state: '', zip_code: '', notes: '', tags: [] });
      fetchLeads();
    } catch (error) {
      toast.error('Failed to create lead');
    }
  };

  // Bulk assign leads to user
  const handleBulkAssign = async () => {
    if (!selectedUserId) {
      toast.error('Please select a user');
      return;
    }
    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(`${API_URL}/api/leads/bulk-assign`, {
        lead_ids: selectedLeads.map(l => l.id),
        user_id: selectedUserId
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success(response.data.message);
      setShowAssignModal(false);
      setSelectedLeads([]);
      setSelectMode(false);
      fetchLeads();
    } catch (error) {
      toast.error('Failed to assign leads');
    }
  };

  // Bulk add leads to sequence
  const handleBulkSequence = async () => {
    if (!selectedSequenceId) {
      toast.error('Please select a sequence');
      return;
    }
    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(`${API_URL}/api/leads/bulk-sequence`, {
        lead_ids: selectedLeads.map(l => l.id),
        sequence_id: selectedSequenceId
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success(response.data.message);
      setShowSequenceModal(false);
      setSelectedLeads([]);
      setSelectMode(false);
    } catch (error) {
      toast.error('Failed to add leads to sequence');
    }
  };

  // Edit lead
  const handleEditLead = (lead) => {
    setEditingLead({
      ...lead,
      mobile: lead.mobile || '',
      street_address: lead.street_address || '',
      city: lead.city || '',
      state: lead.state || '',
      zip_code: lead.zip_code || '',
      notes: lead.notes || ''
    });
    setShowEditModal(true);
  };

  const handleUpdateLead = async () => {
    try {
      const token = localStorage.getItem('token');
      await axios.put(`${API_URL}/api/leads/${editingLead.id}`, editingLead, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Lead updated successfully!');
      setShowEditModal(false);
      setEditingLead(null);
      fetchLeads();
    } catch (error) {
      toast.error('Failed to update lead');
    }
  };

  // Bulk selection handlers
  const toggleSelectMode = () => {
    setSelectMode(!selectMode);
    setSelectedLeads([]);
  };

  const toggleLeadSelection = (lead) => {
    setSelectedLeads(prev => {
      const isSelected = prev.find(l => l.id === lead.id);
      if (isSelected) {
        return prev.filter(l => l.id !== lead.id);
      } else {
        return [...prev, lead];
      }
    });
  };

  const selectAllLeads = () => {
    if (selectedLeads.length === filteredLeads.length) {
      setSelectedLeads([]);
    } else {
      setSelectedLeads([...filteredLeads]);
    }
  };

  // Export leads to CSV
  const exportLeads = (leadsToExport = leads) => {
    const headers = ['First Name', 'Last Name', 'Email', 'Phone', 'Company', 'Title', 'Stage', 'Score'];
    const csvContent = [
      headers.join(','),
      ...leadsToExport.map(lead => [
        lead.first_name || '',
        lead.last_name || '',
        lead.email || '',
        lead.phone || '',
        lead.company || '',
        lead.title || '',
        lead.stage || '',
        lead.score || 0
      ].map(field => `"${String(field).replace(/"/g, '""')}"`).join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `leads_export_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    
    toast.success(`Exported ${leadsToExport.length} leads`);
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setImporting(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(`${API_URL}/api/leads/bulk-import`, formData, {
        headers: { 
          'Content-Type': 'multipart/form-data',
          'Authorization': `Bearer ${token}`
        }
      });
      toast.success(`Imported ${response.data.success} leads successfully!`);
      if (response.data.failed > 0) {
        toast.warning(`${response.data.failed} leads failed to import`);
      }
      setShowImport(false);
      fetchLeads();
    } catch (error) {
      console.error('Import error:', error);
      toast.error('Import failed: ' + (error.response?.data?.detail || 'Unknown error'));
    } finally {
      setImporting(false);
    }
  };

  const handleScrape = async () => {
    if (!scrapeUrl) {
      toast.error('Please enter a website URL');
      return;
    }

    setScraping(true);
    try {
      const response = await axios.post(`${API_URL}/api/leads/scrape`, {
        url: scrapeUrl
      });
      toast.success(response.data.message);
      setShowScraper(false);
      setScrapeUrl('');
      fetchLeads();
    } catch (error) {
      toast.error('Scraping failed: ' + (error.response?.data?.detail || 'Unknown error'));
    } finally {
      setScraping(false);
    }
  };

  const filteredLeads = leads.filter(lead =>
    lead.first_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    lead.last_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    lead.email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    lead.company?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <DashboardLayout>
      <div>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6 lg:mb-8">
          <div>
            <h1 className="text-2xl lg:text-4xl font-bold text-foreground mb-1 lg:mb-2">Leads</h1>
            <p className="text-sm lg:text-base text-secondary">Import, scrape, and manage all your leads</p>
          </div>
          <div className="flex flex-wrap gap-2 lg:gap-3">
            <button
              onClick={() => exportLeads()}
              className="px-3 lg:px-4 py-2 border border-border text-foreground rounded-lg font-medium hover:bg-slate-50 transition-all duration-200 flex items-center gap-2 text-sm"
            >
              <Download className="w-4 h-4" />
              <span className="hidden sm:inline">Export</span>
            </button>
            <button
              onClick={() => setShowImport(true)}
              className="px-3 lg:px-4 py-2 border-2 border-primary text-primary rounded-lg font-semibold hover:bg-primary/10 transition-all duration-200 flex items-center gap-2 text-sm"
            >
              <Upload className="w-4 h-4" />
              <span className="hidden sm:inline">Import</span>
            </button>
            <button
              onClick={() => setShowScraper(true)}
              className="px-3 lg:px-4 py-2 border-2 border-accent text-accent rounded-lg font-semibold hover:bg-accent/10 transition-all duration-200 flex items-center gap-2 text-sm"
            >
              <Globe className="w-4 h-4" />
              <span className="hidden sm:inline">Scrape</span>
            </button>
            <button
              onClick={() => setShowForm(true)}
              className="px-4 lg:px-6 py-2 lg:py-3 bg-primary text-white rounded-lg font-semibold hover:bg-primary/90 transition-all duration-200 flex items-center gap-2 text-sm"
            >
              <Plus className="w-4 h-4" />
              Add Lead
            </button>
          </div>
        </div>

        {/* Import Modal */}
        <AnimatePresence>
          {showImport && (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="bg-white p-8 rounded-xl border border-border mb-6 shadow-lg"
            >
              <h3 className="text-2xl font-bold text-foreground mb-4">Bulk Import Leads</h3>
              <p className="text-secondary mb-6">
                Upload a CSV file with columns: first_name, last_name, email, phone, company, title
              </p>
              <div className="border-2 border-dashed border-border rounded-lg p-12 text-center mb-6 hover:border-primary transition-colors">
                <Upload className="w-16 h-16 text-secondary mx-auto mb-4" />
                <p className="text-lg font-medium text-foreground mb-2">Drop CSV file here or click to browse</p>
                <input
                  type="file"
                  accept=".csv"
                  onChange={handleFileUpload}
                  disabled={importing}
                  className="hidden"
                  id="csv-upload"
                />
                <label
                  htmlFor="csv-upload"
                  className="inline-block px-6 py-3 bg-primary text-white rounded-lg font-semibold hover:bg-primary/90 transition-all cursor-pointer"
                >
                  {importing ? 'Importing...' : 'Select CSV File'}
                </label>
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => setShowImport(false)}
                  className="flex-1 py-3 border-2 border-border rounded-lg font-semibold hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
                <a
                  href="data:text/csv;charset=utf-8,first_name,last_name,email,phone,company,title%0AJohn,Doe,john@example.com,555-0100,Acme Corp,CEO"
                  download="sample-leads.csv"
                  className="flex-1 py-3 border-2 border-primary text-primary rounded-lg font-semibold hover:bg-primary/10 transition-colors text-center flex items-center justify-center gap-2"
                >
                  <Download className="w-5 h-5" />
                  Download Sample CSV
                </a>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Scraper Modal */}
        <AnimatePresence>
          {showScraper && (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="bg-white p-8 rounded-xl border border-border mb-6 shadow-lg"
            >
              <h3 className="text-2xl font-bold text-foreground mb-4">Scrape Website for Leads</h3>
              <p className="text-secondary mb-6">
                Enter a website URL to automatically extract contact information
              </p>
              <div className="mb-6">
                <label className="block text-sm font-medium text-foreground mb-2">Website URL</label>
                <input
                  type="url"
                  value={scrapeUrl}
                  onChange={(e) => setScrapeUrl(e.target.value)}
                  placeholder="https://example.com/about"
                  className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                <p className="text-sm text-blue-800">
                  <strong>Tip:</strong> Best results from About Us, Contact, or Team pages
                </p>
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => setShowScraper(false)}
                  className="flex-1 py-3 border-2 border-border rounded-lg font-semibold hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleScrape}
                  disabled={scraping || !scrapeUrl}
                  className="flex-1 py-3 bg-accent text-white rounded-lg font-semibold hover:bg-accent/90 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {scraping ? 'Scraping...' : 'Start Scraping'}
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Search & Bulk Actions */}
        <div className="mb-6 space-y-4">
          <div className="flex gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-secondary" />
              <input
                type="text"
                placeholder="Search leads..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-12 pr-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <button
              onClick={toggleSelectMode}
              className={`px-4 py-2 rounded-lg font-medium flex items-center gap-2 transition-colors ${
                selectMode 
                  ? 'bg-primary text-white' 
                  : 'border border-border hover:bg-slate-50'
              }`}
            >
              <CheckSquare className="w-5 h-5" />
              {selectMode ? 'Exit Selection' : 'Select Multiple'}
            </button>
          </div>

          {/* Bulk Actions Toolbar */}
          {selectMode && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-center gap-4 p-4 bg-slate-50 rounded-xl border border-border"
            >
              <button
                onClick={selectAllLeads}
                className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium hover:bg-slate-200 rounded transition-colors"
              >
                {selectedLeads.length === filteredLeads.length ? (
                  <CheckSquare className="w-4 h-4 text-primary" />
                ) : (
                  <Square className="w-4 h-4" />
                )}
                {selectedLeads.length === filteredLeads.length ? 'Deselect All' : 'Select All'}
              </button>
              
              <div className="h-6 w-px bg-border" />
              
              <span className="text-sm text-secondary">
                {selectedLeads.length} of {filteredLeads.length} selected
              </span>
              
              <div className="h-6 w-px bg-border" />
              
              <button
                onClick={() => {
                  if (selectedLeads.length === 0) {
                    toast.error('Please select at least one lead');
                    return;
                  }
                  setShowEmailModal(true);
                }}
                disabled={selectedLeads.length === 0}
                className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg text-sm font-medium hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <Mail className="w-4 h-4" />
                Email Selected ({selectedLeads.length})
              </button>
              
              <button
                onClick={() => {
                  if (selectedLeads.length === 0) {
                    toast.error('Please select at least one lead');
                    return;
                  }
                  exportLeads(selectedLeads);
                }}
                disabled={selectedLeads.length === 0}
                className="flex items-center gap-2 px-4 py-2 bg-green-500 text-white rounded-lg text-sm font-medium hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <Download className="w-4 h-4" />
                Export Selected
              </button>
              
              {/* NEW: Assign to User button */}
              <button
                onClick={() => {
                  if (selectedLeads.length === 0) {
                    toast.error('Please select at least one lead');
                    return;
                  }
                  setShowAssignModal(true);
                }}
                disabled={selectedLeads.length === 0}
                className="flex items-center gap-2 px-4 py-2 bg-purple-500 text-white rounded-lg text-sm font-medium hover:bg-purple-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <Users className="w-4 h-4" />
                Assign to User
              </button>
              
              {/* NEW: Add to Sequence button */}
              <button
                onClick={() => {
                  if (selectedLeads.length === 0) {
                    toast.error('Please select at least one lead');
                    return;
                  }
                  setShowSequenceModal(true);
                }}
                disabled={selectedLeads.length === 0}
                className="flex items-center gap-2 px-4 py-2 bg-orange-500 text-white rounded-lg text-sm font-medium hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <Zap className="w-4 h-4" />
                Add to Sequence
              </button>
              
              <button
                onClick={() => {
                  setSelectMode(false);
                  setSelectedLeads([]);
                }}
                className="ml-auto p-2 hover:bg-slate-200 rounded transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </motion.div>
          )}
        </div>

        {/* Manual Add Form */}
        {showForm && (
          <div className="bg-white p-6 rounded-xl border border-border mb-6">
            <h3 className="text-lg font-semibold text-foreground mb-4">Add New Lead</h3>
            <form onSubmit={handleSubmit} className="grid md:grid-cols-2 gap-4">
              <input
                type="text"
                placeholder="First Name"
                value={formData.first_name}
                onChange={(e) => setFormData({...formData, first_name: e.target.value})}
                required
                className="px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <input
                type="text"
                placeholder="Last Name"
                value={formData.last_name}
                onChange={(e) => setFormData({...formData, last_name: e.target.value})}
                required
                className="px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <input
                type="email"
                placeholder="Email"
                value={formData.email}
                onChange={(e) => setFormData({...formData, email: e.target.value})}
                required
                className="px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <input
                type="tel"
                placeholder="Phone"
                value={formData.phone}
                onChange={(e) => setFormData({...formData, phone: e.target.value})}
                className="px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <input
                type="text"
                placeholder="Company"
                value={formData.company}
                onChange={(e) => setFormData({...formData, company: e.target.value})}
                required
                className="px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <input
                type="text"
                placeholder="Title"
                value={formData.title}
                onChange={(e) => setFormData({...formData, title: e.target.value})}
                className="px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <div className="md:col-span-2 flex gap-3">
                <button type="submit" className="flex-1 py-3 bg-primary text-white rounded-lg font-semibold hover:bg-primary/90 transition-all">
                  Create Lead
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
          </div>
        )}

        {/* Leads Grid */}
        <div className="grid gap-4">
          {filteredLeads.map((lead) => {
            const isSelected = selectedLeads.find(l => l.id === lead.id);
            return (
              <div 
                key={lead.id} 
                onClick={() => {
                  if (selectMode) {
                    toggleLeadSelection(lead);
                  } else {
                    navigate(`/leads/${lead.id}`);
                  }
                }}
                className={`bg-white p-6 rounded-xl border-2 transition-all duration-200 cursor-pointer group ${
                  isSelected 
                    ? 'border-primary bg-primary/5' 
                    : 'border-border hover:border-primary'
                }`}
              >
                <div className="flex items-start justify-between">
                  {/* Checkbox for selection mode */}
                  {selectMode && (
                    <div className="mr-4 flex items-center">
                      <div className={`w-6 h-6 rounded border-2 flex items-center justify-center transition-colors ${
                        isSelected ? 'bg-primary border-primary' : 'border-gray-300'
                      }`}>
                        {isSelected && <CheckSquare className="w-4 h-4 text-white" />}
                      </div>
                    </div>
                  )}
                  
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-xl font-semibold text-foreground group-hover:text-primary transition-colors">
                        {lead.first_name} {lead.last_name}
                      </h3>
                      {lead.assigned_to && (
                        <span className="px-2 py-1 bg-green-100 text-green-700 text-xs font-semibold rounded">
                          Assigned
                        </span>
                      )}
                      <span className={`px-2 py-1 text-xs font-semibold rounded capitalize ${
                        lead.stage === 'prospecting' ? 'bg-slate-100 text-slate-700' :
                        lead.stage === 'qualified' ? 'bg-blue-100 text-blue-700' :
                        lead.stage === 'proposal' ? 'bg-yellow-100 text-yellow-700' :
                        lead.stage === 'negotiation' ? 'bg-orange-100 text-orange-700' :
                        'bg-green-100 text-green-700'
                      }`}>
                        {lead.stage}
                      </span>
                    </div>
                    <div className="grid md:grid-cols-3 gap-3 text-sm text-secondary">
                      <div className="flex items-center gap-2">
                        <Mail className="w-4 h-4" />
                        {lead.email}
                      </div>
                      {lead.phone && (
                        <div className="flex items-center gap-2">
                          <Phone className="w-4 h-4" />
                          {lead.phone}
                        </div>
                      )}
                      {lead.mobile && (
                        <div className="flex items-center gap-2">
                          <Phone className="w-4 h-4 text-green-500" />
                          {lead.mobile} (Mobile)
                        </div>
                      )}
                      <div className="flex items-center gap-2">
                        <Building className="w-4 h-4" />
                        {lead.company}
                      </div>
                      {lead.city && lead.state && (
                        <div className="flex items-center gap-2">
                          <MapPin className="w-4 h-4" />
                          {lead.city}, {lead.state}
                        </div>
                      )}
                      {lead.notes && (
                        <div className="flex items-center gap-2 col-span-2">
                          <FileText className="w-4 h-4" />
                          <span className="truncate">{lead.notes}</span>
                        </div>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    {/* Action Buttons */}
                    {!selectMode && (
                      <>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleEditLead(lead);
                          }}
                          className="p-2 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
                          title="Edit Lead"
                        >
                          <Edit2 className="w-5 h-5 text-slate-600" />
                        </button>
                        {(lead.phone || lead.mobile) && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedLeadForDialer(lead);
                              setShowDialer(true);
                            }}
                            className="p-2 bg-green-100 rounded-lg hover:bg-green-200 transition-colors"
                            title="Call Lead"
                          >
                            <PhoneCall className="w-5 h-5 text-green-600" />
                          </button>
                        )}
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedLeadForEmail(lead);
                            setShowEmailModal(true);
                          }}
                          className="p-2 bg-blue-100 rounded-lg hover:bg-blue-200 transition-colors"
                          title="Email Lead"
                        >
                          <Mail className="w-5 h-5 text-blue-600" />
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedLeadForMeeting(lead);
                            setShowMeetingModal(true);
                          }}
                          className="p-2 bg-purple-100 rounded-lg hover:bg-purple-200 transition-colors"
                          title="Schedule Meeting"
                        >
                          <Calendar className="w-5 h-5 text-purple-600" />
                        </button>
                      </>
                    )}
                    <div className="text-right ml-2">
                      <div className="text-2xl font-bold metric-value text-primary mb-1">{lead.score}</div>
                      <div className="text-xs text-secondary">Lead Score</div>
                    </div>
                    {!selectMode && (
                      <ChevronRight className="w-5 h-5 text-secondary group-hover:text-primary transition-colors" />
                    )}
                  </div>
                </div>
                {lead.ai_insights && (
                  <div className="mt-4 p-3 bg-orange-50 border border-orange-200 rounded-lg">
                    <p className="text-sm text-foreground">{lead.ai_insights}</p>
                  </div>
                )}
              </div>
            );
          })}
          {filteredLeads.length === 0 && (
            <p className="text-center text-secondary py-12">No leads found</p>
          )}
        </div>
      </div>

      {/* Call Modal */}
      <CallModal
        isOpen={showCallModal}
        onClose={() => {
          setShowCallModal(false);
          setSelectedLeadForCall(null);
        }}
        lead={selectedLeadForCall}
        onCallLogged={fetchLeads}
      />

      {/* Email Modal */}
      <EmailModal
        isOpen={showEmailModal}
        onClose={() => {
          setShowEmailModal(false);
          setSelectedLeadForEmail(null);
        }}
        leads={selectedLeads.length > 0 ? selectedLeads : []}
        singleLead={selectedLeadForEmail}
      />

      {/* Meeting Modal */}
      <MeetingModal
        isOpen={showMeetingModal}
        onClose={() => {
          setShowMeetingModal(false);
          setSelectedLeadForMeeting(null);
        }}
        lead={selectedLeadForMeeting}
        onMeetingScheduled={fetchLeads}
      />

      {/* Phone Dialer */}
      <PhoneDialer
        isOpen={showDialer}
        onClose={() => {
          setShowDialer(false);
          setSelectedLeadForDialer(null);
        }}
        prefilledNumber={selectedLeadForDialer?.phone || selectedLeadForDialer?.mobile || ''}
        leadInfo={selectedLeadForDialer}
      />

      {/* Assign Leads Modal */}
      <AnimatePresence>
        {showAssignModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-white rounded-2xl w-full max-w-md p-6"
            >
              <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
                <Users className="w-6 h-6 text-purple-600" />
                Assign {selectedLeads.length} Lead(s)
              </h2>
              <p className="text-secondary mb-4">Select a user to assign these leads to:</p>
              
              <select
                value={selectedUserId}
                onChange={(e) => setSelectedUserId(e.target.value)}
                className="w-full px-4 py-3 border border-border rounded-lg mb-4 focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="">Select User...</option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>{u.full_name} ({u.email})</option>
                ))}
              </select>
              
              <div className="flex gap-3">
                <button
                  onClick={() => setShowAssignModal(false)}
                  className="flex-1 px-4 py-2 border border-border rounded-lg hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleBulkAssign}
                  disabled={!selectedUserId}
                  className="flex-1 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
                >
                  Assign Leads
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Add to Sequence Modal */}
      <AnimatePresence>
        {showSequenceModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-white rounded-2xl w-full max-w-md p-6"
            >
              <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
                <Zap className="w-6 h-6 text-orange-600" />
                Add {selectedLeads.length} Lead(s) to Sequence
              </h2>
              <p className="text-secondary mb-4">Select an email sequence:</p>
              
              <select
                value={selectedSequenceId}
                onChange={(e) => setSelectedSequenceId(e.target.value)}
                className="w-full px-4 py-3 border border-border rounded-lg mb-4 focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="">Select Sequence...</option>
                {sequences.map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
              
              {sequences.length === 0 && (
                <p className="text-sm text-yellow-600 mb-4">No sequences found. Create a sequence first in the Sequences page.</p>
              )}
              
              <div className="flex gap-3">
                <button
                  onClick={() => setShowSequenceModal(false)}
                  className="flex-1 px-4 py-2 border border-border rounded-lg hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleBulkSequence}
                  disabled={!selectedSequenceId}
                  className="flex-1 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50"
                >
                  Add to Sequence
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Edit Lead Modal */}
      <AnimatePresence>
        {showEditModal && editingLead && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 overflow-y-auto">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-white rounded-2xl w-full max-w-2xl p-6 my-8"
            >
              <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
                <Edit2 className="w-6 h-6 text-primary" />
                Edit Lead
              </h2>
              
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">First Name</label>
                  <input
                    type="text"
                    value={editingLead.first_name}
                    onChange={(e) => setEditingLead({...editingLead, first_name: e.target.value})}
                    className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Last Name</label>
                  <input
                    type="text"
                    value={editingLead.last_name}
                    onChange={(e) => setEditingLead({...editingLead, last_name: e.target.value})}
                    className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Email</label>
                  <input
                    type="email"
                    value={editingLead.email}
                    onChange={(e) => setEditingLead({...editingLead, email: e.target.value})}
                    className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Phone</label>
                  <input
                    type="tel"
                    value={editingLead.phone || ''}
                    onChange={(e) => setEditingLead({...editingLead, phone: e.target.value})}
                    className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Mobile</label>
                  <input
                    type="tel"
                    value={editingLead.mobile || ''}
                    onChange={(e) => setEditingLead({...editingLead, mobile: e.target.value})}
                    className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Company</label>
                  <input
                    type="text"
                    value={editingLead.company}
                    onChange={(e) => setEditingLead({...editingLead, company: e.target.value})}
                    className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Title</label>
                  <input
                    type="text"
                    value={editingLead.title || ''}
                    onChange={(e) => setEditingLead({...editingLead, title: e.target.value})}
                    className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium mb-1">Street Address</label>
                  <input
                    type="text"
                    value={editingLead.street_address || ''}
                    onChange={(e) => setEditingLead({...editingLead, street_address: e.target.value})}
                    className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">City</label>
                  <input
                    type="text"
                    value={editingLead.city || ''}
                    onChange={(e) => setEditingLead({...editingLead, city: e.target.value})}
                    className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">State</label>
                  <input
                    type="text"
                    value={editingLead.state || ''}
                    onChange={(e) => setEditingLead({...editingLead, state: e.target.value})}
                    className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">ZIP Code</label>
                  <input
                    type="text"
                    value={editingLead.zip_code || ''}
                    onChange={(e) => setEditingLead({...editingLead, zip_code: e.target.value})}
                    className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium mb-1">Notes</label>
                  <textarea
                    value={editingLead.notes || ''}
                    onChange={(e) => setEditingLead({...editingLead, notes: e.target.value})}
                    rows={3}
                    className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="Add notes about this lead..."
                  />
                </div>
              </div>
              
              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => {
                    setShowEditModal(false);
                    setEditingLead(null);
                  }}
                  className="flex-1 px-4 py-2 border border-border rounded-lg hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleUpdateLead}
                  className="flex-1 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 flex items-center justify-center gap-2"
                >
                  <Save className="w-4 h-4" />
                  Save Changes
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </DashboardLayout>
  );
};

export default LeadsPage;