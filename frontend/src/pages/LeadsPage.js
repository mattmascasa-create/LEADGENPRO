import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Plus, Search, Mail, Phone, Building } from 'lucide-react';
import { toast } from 'react-toastify';
import DashboardLayout from '@/components/DashboardLayout';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const LeadsPage = () => {
  const [leads, setLeads] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [showForm, setShowForm] = useState(false);
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
  }, []);

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

  const filteredLeads = leads.filter(lead =>
    lead.first_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    lead.last_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    lead.email.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <DashboardLayout>
      <div>
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-4xl font-bold text-foreground mb-2">Leads</h1>
            <p className="text-secondary">Manage and track all your leads</p>
          </div>
          <button
            onClick={() => setShowForm(!showForm)}
            className="px-6 py-3 bg-primary text-white rounded-lg font-semibold hover:bg-primary/90 transition-all duration-200 flex items-center gap-2"
          >
            <Plus className="w-5 h-5" />
            Add Lead
          </button>
        </div>

        {/* Search */}
        <div className="mb-6">
          <div className="relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-secondary" />
            <input
              type="text"
              placeholder="Search leads..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-12 pr-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
        </div>

        {/* Add Form */}
        {showForm && (
          <div className="bg-white p-6 rounded-xl border border-border mb-6">
            <h3 className="text-lg font-semibold text-foreground mb-4">New Lead</h3>
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
          {filteredLeads.map((lead) => (
            <div key={lead.id} className="bg-white p-6 rounded-xl border border-border hover:border-primary transition-all duration-200">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="text-xl font-semibold text-foreground mb-2">
                    {lead.first_name} {lead.last_name}
                  </h3>
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
                <div className="text-right">
                  <div className="text-2xl font-bold metric-value text-primary mb-1">{lead.score}</div>
                  <div className="text-xs text-secondary">Lead Score</div>
                </div>
              </div>
              {lead.ai_insights && (
                <div className="mt-4 p-3 bg-orange-50 border border-orange-200 rounded-lg">
                  <p className="text-sm text-foreground">{lead.ai_insights}</p>
                </div>
              )}
            </div>
          ))}
          {filteredLeads.length === 0 && (
            <p className="text-center text-secondary py-12">No leads found</p>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
};

export default LeadsPage;