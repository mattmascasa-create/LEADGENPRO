import React, { useEffect, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { motion } from 'framer-motion';
import { Plus, Search, Mail, Phone, Building, Trash2, Edit, LogOut } from 'lucide-react';
import { toast } from 'react-toastify';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const LeadsPage = () => {
  const { user, logout } = useAuth();
  const [leads, setLeads] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    company: '',
    status: 'new'
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
      setFormData({
        first_name: '',
        last_name: '',
        email: '',
        phone: '',
        company: '',
        status: 'new'
      });
      fetchLeads();
    } catch (error) {
      toast.error('Failed to create lead');
    }
  };

  const handleDelete = async (leadId) => {
    if (!window.confirm('Are you sure you want to delete this lead?')) return;
    
    try {
      await axios.delete(`${API_URL}/api/leads/${leadId}`);
      toast.success('Lead deleted successfully');
      fetchLeads();
    } catch (error) {
      toast.error('Failed to delete lead');
    }
  };

  const filteredLeads = leads.filter(lead => 
    lead.first_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    lead.last_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    lead.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
    lead.company.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getStatusColor = (status) => {
    const colors = {
      new: 'bg-primary/10 text-primary',
      contacted: 'bg-yellow-500/10 text-yellow-500',
      qualified: 'bg-green-500/10 text-green-500',
      closed: 'bg-accent/10 text-accent'
    };
    return colors[status] || colors.new;
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Navigation */}
      <nav className="glassmorphism border-b border-border sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-12 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-8">
              <h1 className="text-2xl font-black text-primary">LeadGen Pro</h1>
              <div className="hidden md:flex gap-4">
                <Link to="/dashboard" className="px-4 py-2 rounded-lg hover:bg-primary/10 text-foreground transition-colors">
                  Dashboard
                </Link>
                <Link to="/leads" className="px-4 py-2 rounded-lg bg-primary/10 text-primary font-semibold">
                  Leads
                </Link>
                <Link to="/appointments" className="px-4 py-2 rounded-lg hover:bg-primary/10 text-foreground transition-colors">
                  Appointments
                </Link>
              </div>
            </div>
            <button
              onClick={logout}
              className="p-2 rounded-lg hover:bg-destructive/10 text-destructive transition-colors"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-12 py-8">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-8">
          <div>
            <h2 className="text-4xl font-black mb-2">Leads</h2>
            <p className="text-muted-foreground">Manage your sales pipeline</p>
          </div>
          <button
            onClick={() => setShowForm(!showForm)}
            className="px-6 py-3 bg-primary text-primary-foreground rounded-lg font-bold flex items-center gap-2 hover:scale-105 transition-transform glow-effect"
          >
            <Plus className="w-5 h-5" />
            Add Lead
          </button>
        </div>

        {/* Search Bar */}
        <div className="mb-6">
          <div className="relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search leads..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-12 pr-4 py-3 bg-secondary border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
        </div>

        {/* Add Lead Form */}
        {showForm && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            className="glassmorphism p-6 rounded-xl mb-6"
          >
            <h3 className="text-xl font-bold mb-4">New Lead</h3>
            <form onSubmit={handleSubmit} className="grid md:grid-cols-2 gap-4">
              <input
                type="text"
                placeholder="First Name"
                value={formData.first_name}
                onChange={(e) => setFormData({...formData, first_name: e.target.value})}
                required
                className="px-4 py-3 bg-secondary border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <input
                type="text"
                placeholder="Last Name"
                value={formData.last_name}
                onChange={(e) => setFormData({...formData, last_name: e.target.value})}
                required
                className="px-4 py-3 bg-secondary border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <input
                type="email"
                placeholder="Email"
                value={formData.email}
                onChange={(e) => setFormData({...formData, email: e.target.value})}
                required
                className="px-4 py-3 bg-secondary border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <input
                type="tel"
                placeholder="Phone"
                value={formData.phone}
                onChange={(e) => setFormData({...formData, phone: e.target.value})}
                className="px-4 py-3 bg-secondary border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <input
                type="text"
                placeholder="Company"
                value={formData.company}
                onChange={(e) => setFormData({...formData, company: e.target.value})}
                required
                className="px-4 py-3 bg-secondary border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <select
                value={formData.status}
                onChange={(e) => setFormData({...formData, status: e.target.value})}
                className="px-4 py-3 bg-secondary border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="new">New</option>
                <option value="contacted">Contacted</option>
                <option value="qualified">Qualified</option>
                <option value="closed">Closed</option>
              </select>
              <div className="md:col-span-2 flex gap-3">
                <button
                  type="submit"
                  className="flex-1 py-3 bg-primary text-primary-foreground rounded-lg font-bold hover:scale-105 transition-transform"
                >
                  Create Lead
                </button>
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="px-6 py-3 border-2 border-border rounded-lg font-bold hover:bg-secondary transition-colors"
                >
                  Cancel
                </button>
              </div>
            </form>
          </motion.div>
        )}

        {/* Leads Grid */}
        <div className="grid gap-4">
          {filteredLeads.map((lead, index) => (
            <motion.div
              key={lead.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className="glassmorphism p-6 rounded-xl hover:border-primary transition-all"
            >
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-xl font-bold">
                      {lead.first_name} {lead.last_name}
                    </h3>
                    <span className={`px-3 py-1 rounded-full text-xs font-semibold ${getStatusColor(lead.status)}`}>
                      {lead.status}
                    </span>
                  </div>
                  <div className="grid md:grid-cols-3 gap-3 text-sm text-muted-foreground">
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
                <div className="flex gap-2">
                  <button
                    onClick={() => handleDelete(lead.id)}
                    className="p-2 bg-destructive/10 text-destructive rounded-lg hover:bg-destructive/20 transition-colors"
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                </div>
              </div>
            </motion.div>
          ))}

          {filteredLeads.length === 0 && (
            <div className="text-center py-12 text-muted-foreground">
              <p className="text-lg">No leads found</p>
              <p className="text-sm">Create your first lead to get started!</p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

export default LeadsPage;