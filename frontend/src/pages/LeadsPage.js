import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { Plus, Search, Mail, Phone, Building, Upload, Globe, Download, Filter, ChevronRight, PhoneCall, Calendar, CheckSquare, Square, X } from 'lucide-react';
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
  const [searchTerm, setSearchTerm] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [showScraper, setShowScraper] = useState(false);
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
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    company: '',
    title: '',
    tags: []
  });

  useEffect(() => {
    fetchLeads();
    
    // Handle query params from copilot
    const action = searchParams.get('action');
    if (action === 'import') setShowImport(true);
    if (action === 'scrape') setShowScraper(true);
    if (action === 'create') setShowForm(true);
  }, [searchParams]);

  const fetchLeads = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/leads`);
      setLeads(response.data);
    } catch (error) {
      toast.error('Failed to load leads');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API_URL}/api/leads`, formData);
      toast.success('Lead created successfully!');
      setShowForm(false);
      setFormData({ first_name: '', last_name: '', email: '', phone: '', company: '', title: '', tags: [] });
      fetchLeads();
    } catch (error) {
      toast.error('Failed to create lead');
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
      const response = await axios.post(`${API_URL}/api/leads/bulk-import`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      toast.success(`Imported ${response.data.success} leads successfully!`);
      if (response.data.failed > 0) {
        toast.warning(`${response.data.failed} leads failed to import`);
      }
      setShowImport(false);
      fetchLeads();
    } catch (error) {
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
                      <div className="flex items-center gap-2">
                        <Building className="w-4 h-4" />
                        {lead.company}
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    {/* Action Buttons */}
                    {!selectMode && (
                      <>
                        {lead.phone && (
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
        prefilledNumber={selectedLeadForDialer?.phone || ''}
        leadInfo={selectedLeadForDialer}
      />
    </DashboardLayout>
  );
};

export default LeadsPage;