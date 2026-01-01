import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import { Plus, Calendar as CalendarIcon, Clock, Video, Link as LinkIcon, Copy, Check } from 'lucide-react';
import { toast } from 'react-toastify';
import { format, addDays, startOfWeek, addWeeks } from 'date-fns';
import DashboardLayout from '@/components/DashboardLayout';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const AppointmentsPage = () => {
  const [appointments, setAppointments] = useState([]);
  const [leads, setLeads] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [showBookingLink, setShowBookingLink] = useState(false);
  const [copied, setCopied] = useState(false);
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [formData, setFormData] = useState({
    title: '',
    lead_id: '',
    employee_id: '',
    scheduled_at: '',
    duration: 30,
    meeting_link: '',
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
      setFormData({ title: '', lead_id: '', employee_id: '', scheduled_at: '', duration: 30, meeting_link: '', notes: '' });
      fetchAppointments();
    } catch (error) {
      toast.error('Failed to create appointment');
    }
  };

  const bookingLink = `${window.location.origin}/book/user-123`;

  const copyBookingLink = () => {
    navigator.clipboard.writeText(bookingLink);
    setCopied(true);
    toast.success('Booking link copied!');
    setTimeout(() => setCopied(false), 2000);
  };

  const getWeekDays = () => {
    const start = startOfWeek(selectedDate, { weekStartsOn: 1 });
    return Array.from({ length: 7 }, (_, i) => addDays(start, i));
  };

  const timeSlots = Array.from({ length: 12 }, (_, i) => `${9 + i}:00`);

  return (
    <DashboardLayout>
      <div>
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-4xl font-bold text-foreground mb-2">Calendar & Appointments</h1>
            <p className="text-secondary">Manage your schedule and share booking links</p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => setShowBookingLink(!showBookingLink)}
              className="px-6 py-3 border-2 border-primary text-primary rounded-lg font-semibold hover:bg-primary/10 transition-all duration-200 flex items-center gap-2"
            >
              <LinkIcon className="w-5 h-5" />
              Booking Link
            </button>
            <button
              onClick={() => setShowForm(!showForm)}
              className="px-6 py-3 bg-primary text-white rounded-lg font-semibold hover:bg-primary/90 transition-all duration-200 flex items-center gap-2"
            >
              <Plus className="w-5 h-5" />
              Schedule Meeting
            </button>
          </div>
        </div>

        {/* Booking Link Modal */}
        {showBookingLink && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white p-8 rounded-xl border border-border mb-6 shadow-lg"
          >
            <h3 className="text-2xl font-bold text-foreground mb-4">Your Booking Link</h3>
            <p className="text-secondary mb-6">Share this link with prospects to let them book time with you automatically</p>
            <div className="flex items-center gap-3 mb-6">
              <div className="flex-1 px-4 py-3 bg-slate-50 border border-border rounded-lg font-mono text-sm text-foreground">
                {bookingLink}
              </div>
              <button
                onClick={copyBookingLink}
                className="px-6 py-3 bg-primary text-white rounded-lg font-semibold hover:bg-primary/90 transition-all duration-200 flex items-center gap-2"
              >
                {copied ? <Check className="w-5 h-5" /> : <Copy className="w-5 h-5" />}
                {copied ? 'Copied!' : 'Copy'}
              </button>
            </div>
            <div className="grid md:grid-cols-3 gap-4">
              <div className="p-4 bg-slate-50 rounded-lg">
                <Clock className="w-6 h-6 text-primary mb-2" />
                <h4 className="font-semibold text-foreground mb-1">30 min slots</h4>
                <p className="text-sm text-secondary">Customizable duration</p>
              </div>
              <div className="p-4 bg-slate-50 rounded-lg">
                <Video className="w-6 h-6 text-primary mb-2" />
                <h4 className="font-semibold text-foreground mb-1">Auto video link</h4>
                <p className="text-sm text-secondary">Zoom/Meet integration</p>
              </div>
              <div className="p-4 bg-slate-50 rounded-lg">
                <CalendarIcon className="w-6 h-6 text-primary mb-2" />
                <h4 className="font-semibold text-foreground mb-1">Calendar sync</h4>
                <p className="text-sm text-secondary">Google/Outlook</p>
              </div>
            </div>
          </motion.div>
        )}

        {/* Schedule Form */}
        {showForm && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white p-6 rounded-xl border border-border mb-6"
          >
            <h3 className="text-xl font-semibold text-foreground mb-4">Schedule New Meeting</h3>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid md:grid-cols-2 gap-4">
                <input
                  type="text"
                  placeholder="Meeting Title"
                  value={formData.title}
                  onChange={(e) => setFormData({...formData, title: e.target.value})}
                  required
                  className="px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                />
                <select
                  value={formData.lead_id}
                  onChange={(e) => setFormData({...formData, lead_id: e.target.value})}
                  required
                  className="px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="">Select Lead</option>
                  {leads.map(lead => (
                    <option key={lead.id} value={lead.id}>
                      {lead.first_name} {lead.last_name} - {lead.company}
                    </option>
                  ))}
                </select>
              </div>
              <div className="grid md:grid-cols-2 gap-4">
                <input
                  type="datetime-local"
                  value={formData.scheduled_at}
                  onChange={(e) => setFormData({...formData, scheduled_at: e.target.value})}
                  required
                  className="px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                />
                <select
                  value={formData.duration}
                  onChange={(e) => setFormData({...formData, duration: parseInt(e.target.value)})}
                  className="px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value={15}>15 minutes</option>
                  <option value={30}>30 minutes</option>
                  <option value={60}>60 minutes</option>
                </select>
              </div>
              <input
                type="url"
                placeholder="Meeting Link (Zoom, Meet, etc.)"
                value={formData.meeting_link}
                onChange={(e) => setFormData({...formData, meeting_link: e.target.value})}
                className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <textarea
                placeholder="Notes (optional)"
                value={formData.notes}
                onChange={(e) => setFormData({...formData, notes: e.target.value})}
                rows={3}
                className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary resize-none"
              />
              <div className="flex gap-3">
                <button type="submit" className="flex-1 py-3 bg-primary text-white rounded-lg font-semibold hover:bg-primary/90 transition-all">
                  Schedule Meeting
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

        {/* Calendar View */}
        <div className="bg-white rounded-xl border border-border overflow-hidden mb-6">
          <div className="p-6 border-b border-border flex items-center justify-between">
            <h3 className="text-xl font-semibold text-foreground">Week of {format(selectedDate, 'MMM d, yyyy')}</h3>
            <div className="flex gap-2">
              <button
                onClick={() => setSelectedDate(addWeeks(selectedDate, -1))}
                className="px-4 py-2 border border-border rounded-lg hover:bg-slate-50 transition-colors"
              >
                Previous
              </button>
              <button
                onClick={() => setSelectedDate(new Date())}
                className="px-4 py-2 border border-border rounded-lg hover:bg-slate-50 transition-colors"
              >
                Today
              </button>
              <button
                onClick={() => setSelectedDate(addWeeks(selectedDate, 1))}
                className="px-4 py-2 border border-border rounded-lg hover:bg-slate-50 transition-colors"
              >
                Next
              </button>
            </div>
          </div>
          <div className="overflow-x-auto">
            <div className="min-w-[800px]">
              <div className="grid grid-cols-8 border-b border-border">
                <div className="p-4 bg-slate-50"></div>
                {getWeekDays().map((day, index) => (
                  <div key={index} className="p-4 text-center border-l border-border bg-slate-50">
                    <div className="text-sm text-secondary">{format(day, 'EEE')}</div>
                    <div className="text-lg font-semibold text-foreground">{format(day, 'd')}</div>
                  </div>
                ))}
              </div>
              {timeSlots.map((time, index) => (
                <div key={index} className="grid grid-cols-8 border-b border-border hover:bg-slate-50 transition-colors">
                  <div className="p-4 text-sm text-secondary border-r border-border">{time}</div>
                  {getWeekDays().map((day, dayIndex) => (
                    <div key={dayIndex} className="p-2 border-l border-border min-h-[60px]"></div>
                  ))}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Upcoming Appointments */}
        <div>
          <h3 className="text-2xl font-semibold text-foreground mb-4">Upcoming Appointments</h3>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {appointments.map((apt, index) => (
              <motion.div
                key={apt.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                className="bg-white p-6 rounded-xl border border-border hover:border-primary transition-all duration-200"
              >
                <h4 className="text-lg font-semibold text-foreground mb-3">{apt.title}</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center gap-2 text-secondary">
                    <CalendarIcon className="w-4 h-4" />
                    {format(new Date(apt.scheduled_at), 'PPP')}
                  </div>
                  <div className="flex items-center gap-2 text-secondary">
                    <Clock className="w-4 h-4" />
                    {format(new Date(apt.scheduled_at), 'p')} ({apt.duration} min)
                  </div>
                  {apt.meeting_link && (
                    <a
                      href={apt.meeting_link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 text-primary hover:underline"
                    >
                      <Video className="w-4 h-4" />
                      Join Meeting
                    </a>
                  )}
                </div>
                {apt.notes && (
                  <p className="mt-3 text-sm text-secondary bg-slate-50 p-3 rounded-lg">{apt.notes}</p>
                )}
              </motion.div>
            ))}
            {appointments.length === 0 && (
              <div className="col-span-full text-center py-12">
                <CalendarIcon className="w-16 h-16 text-secondary mx-auto mb-4" />
                <p className="text-lg text-secondary">No upcoming appointments</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default AppointmentsPage;