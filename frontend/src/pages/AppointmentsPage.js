import React, { useEffect, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { motion } from 'framer-motion';
import { Plus, Calendar as CalendarIcon, Clock, User, LogOut } from 'lucide-react';
import { toast } from 'react-toastify';
import { format } from 'date-fns';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const AppointmentsPage = () => {
  const { user, logout } = useAuth();
  const [appointments, setAppointments] = useState([]);
  const [leads, setLeads] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    title: '',
    lead_id: '',
    employee_id: user?.id || '',
    scheduled_at: '',
    notes: ''
  });

  useEffect(() => {
    fetchAppointments();
    fetchLeads();
  }, []);

  const fetchAppointments = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/appointments`);
      setAppointments(response.data);
    } catch (error) {
      toast.error('Failed to load appointments');
    }
  };

  const fetchLeads = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/leads`);
      setLeads(response.data);
    } catch (error) {
      console.error('Failed to load leads');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API_URL}/api/appointments`, {
        ...formData,
        scheduled_at: new Date(formData.scheduled_at).toISOString()
      });
      toast.success('Appointment created successfully!');
      setShowForm(false);
      setFormData({
        title: '',
        lead_id: '',
        employee_id: user?.id || '',
        scheduled_at: '',
        notes: ''
      });
      fetchAppointments();
    } catch (error) {
      toast.error('Failed to create appointment');
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      scheduled: 'bg-primary/10 text-primary',
      completed: 'bg-green-500/10 text-green-500',
      cancelled: 'bg-destructive/10 text-destructive'
    };
    return colors[status] || colors.scheduled;
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
                <Link to="/leads" className="px-4 py-2 rounded-lg hover:bg-primary/10 text-foreground transition-colors">
                  Leads
                </Link>
                <Link to="/appointments" className="px-4 py-2 rounded-lg bg-primary/10 text-primary font-semibold">
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
            <h2 className="text-4xl font-black mb-2">Appointments</h2>
            <p className="text-muted-foreground">Manage your scheduled meetings</p>
          </div>
          <button
            onClick={() => setShowForm(!showForm)}
            className="px-6 py-3 bg-accent text-accent-foreground rounded-lg font-bold flex items-center gap-2 hover:scale-105 transition-transform glow-effect"
          >
            <Plus className="w-5 h-5" />
            Schedule Appointment
          </button>
        </div>

        {/* Add Appointment Form */}
        {showForm && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            className="glassmorphism p-6 rounded-xl mb-6"
          >
            <h3 className="text-xl font-bold mb-4">New Appointment</h3>
            <form onSubmit={handleSubmit} className="space-y-4">
              <input
                type="text"
                placeholder="Appointment Title"
                value={formData.title}
                onChange={(e) => setFormData({...formData, title: e.target.value})}
                required
                className="w-full px-4 py-3 bg-secondary border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <select
                value={formData.lead_id}
                onChange={(e) => setFormData({...formData, lead_id: e.target.value})}
                required
                className="w-full px-4 py-3 bg-secondary border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="">Select Lead</option>
                {leads.map(lead => (
                  <option key={lead.id} value={lead.id}>
                    {lead.first_name} {lead.last_name} - {lead.company}
                  </option>
                ))}
              </select>
              <input
                type="datetime-local"
                value={formData.scheduled_at}
                onChange={(e) => setFormData({...formData, scheduled_at: e.target.value})}
                required
                className="w-full px-4 py-3 bg-secondary border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <textarea
                placeholder="Notes (optional)"
                value={formData.notes}
                onChange={(e) => setFormData({...formData, notes: e.target.value})}
                rows={3}
                className="w-full px-4 py-3 bg-secondary border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary resize-none"
              />
              <div className="flex gap-3">
                <button
                  type="submit"
                  className="flex-1 py-3 bg-accent text-accent-foreground rounded-lg font-bold hover:scale-105 transition-transform"
                >
                  Create Appointment
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

        {/* Appointments Grid */}
        <div className="grid gap-4">
          {appointments.map((appointment, index) => (
            <motion.div
              key={appointment.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className="glassmorphism p-6 rounded-xl hover:border-accent transition-all"
            >
              <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-3">
                    <h3 className="text-xl font-bold">{appointment.title}</h3>
                    <span className={`px-3 py-1 rounded-full text-xs font-semibold ${getStatusColor(appointment.status)}`}>
                      {appointment.status}
                    </span>
                  </div>
                  <div className="space-y-2 text-sm text-muted-foreground">
                    <div className="flex items-center gap-2">
                      <CalendarIcon className="w-4 h-4" />
                      {format(new Date(appointment.scheduled_at), 'PPP')}
                    </div>
                    <div className="flex items-center gap-2">
                      <Clock className="w-4 h-4" />
                      {format(new Date(appointment.scheduled_at), 'p')}
                    </div>
                    {appointment.notes && (
                      <div className="mt-3 p-3 bg-secondary rounded-lg">
                        <p className="text-xs">{appointment.notes}</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </motion.div>
          ))}

          {appointments.length === 0 && (
            <div className="text-center py-12 text-muted-foreground">
              <CalendarIcon className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <p className="text-lg">No appointments scheduled</p>
              <p className="text-sm">Create your first appointment to get started!</p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

export default AppointmentsPage;