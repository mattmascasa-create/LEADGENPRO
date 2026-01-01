import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Calendar, Clock, Video, Users, Plus, Link as LinkIcon, Copy, Check, Search } from 'lucide-react';
import { toast } from 'react-toastify';
import { format, addDays, startOfWeek } from 'date-fns';
import { motion } from 'framer-motion';
import DashboardLayout from '@/components/DashboardLayout';
import { useAuth } from '@/context/AuthContext';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const MeetingsPage = () => {
  const { user } = useAuth();
  const [appointments, setAppointments] = useState([]);
  const [leads, setLeads] = useState([]);
  const [teamMembers, setTeamMembers] = useState([]);
  const [showQuickScheduler, setShowQuickScheduler] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [quickForm, setQuickForm] = useState({
    type: 'team',  // team, lead, external
    title: '',
    attendees: [],
    lead_id: '',
    scheduled_at: '',
    duration: 30,
    meeting_link: ''
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [aptsRes, leadsRes, usersRes] = await Promise.all([
        axios.get(`${API_URL}/api/appointments`),
        axios.get(`${API_URL}/api/leads`),
        axios.get(`${API_URL}/api/users`)
      ]);
      setAppointments(aptsRes.data);
      setLeads(leadsRes.data);
      setTeamMembers(usersRes.data);
    } catch (error) {
      toast.error('Failed to load data');
    }
  };

  const handleQuickSchedule = async () => {
    if (!quickForm.title || !quickForm.scheduled_at) {
      toast.error('Please fill in required fields');
      return;
    }

    try {
      let meetingLink = quickForm.meeting_link;
      if (!meetingLink) {
        meetingLink = `https://meet.leadgenpro.com/${Date.now()}`;
      }

      await axios.post(`${API_URL}/api/appointments`, {
        title: quickForm.title,
        lead_id: quickForm.lead_id || 'team-meeting',
        employee_id: user.id,
        scheduled_at: new Date(quickForm.scheduled_at).toISOString(),
        duration: quickForm.duration,
        meeting_link: meetingLink,
        notes: `Attendees: ${quickForm.attendees.map(a => a.full_name).join(', ')}`
      });

      toast.success('Meeting scheduled successfully!');
      setShowQuickScheduler(false);
      setQuickForm({ type: 'team', title: '', attendees: [], lead_id: '', scheduled_at: '', duration: 30, meeting_link: '' });
      fetchData();
    } catch (error) {
      toast.error('Failed to schedule meeting');
    }
  };

  const copyMeetingLink = (link) => {
    navigator.clipboard.writeText(link);
    toast.success('Meeting link copied!');
  };

  const toggleAttendee = (person) => {
    setQuickForm(prev => ({
      ...prev,
      attendees: prev.attendees.find(a => a.id === person.id)
        ? prev.attendees.filter(a => a.id !== person.id)
        : [...prev.attendees, person]
    }));
  };

  const filteredLeads = leads.filter(l =>
    l.first_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    l.last_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    l.company.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const upcomingMeetings = appointments.filter(a => new Date(a.scheduled_at) > new Date());
  const pastMeetings = appointments.filter(a => new Date(a.scheduled_at) <= new Date());

  return (
    <DashboardLayout>
      <div>
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-4xl font-bold text-foreground mb-2">Meetings</h1>
            <p className="text-secondary">Schedule and manage all your meetings in one place</p>
          </div>
          <button
            onClick={() => setShowQuickScheduler(true)}
            className="px-6 py-3 bg-primary text-white rounded-lg font-semibold hover:bg-primary/90 transition-all duration-200 flex items-center gap-2 shadow-lg"
          >
            <Plus className="w-5 h-5" />
            Quick Schedule
          </button>
        </div>

        {/* Quick Stats */}
        <div className="grid md:grid-cols-3 gap-6 mb-8">
          <div className="bg-gradient-to-br from-blue-500 to-blue-600 p-6 rounded-xl text-white">
            <Calendar className="w-10 h-10 mb-3 opacity-80" />
            <div className="text-3xl font-bold metric-value mb-1">{upcomingMeetings.length}</div>
            <div className="text-blue-100">Upcoming Meetings</div>
          </div>
          <div className="bg-gradient-to-br from-green-500 to-green-600 p-6 rounded-xl text-white">
            <Users className="w-10 h-10 mb-3 opacity-80" />
            <div className="text-3xl font-bold metric-value mb-1">{teamMembers.length}</div>
            <div className="text-green-100">Team Members</div>
          </div>
          <div className="bg-gradient-to-br from-purple-500 to-purple-600 p-6 rounded-xl text-white">
            <Video className="w-10 h-10 mb-3 opacity-80" />
            <div className="text-3xl font-bold metric-value mb-1">{pastMeetings.length}</div>
            <div className="text-purple-100">Meetings Completed</div>
          </div>
        </div>

        {/* Upcoming Meetings */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-foreground mb-4">Upcoming Meetings</h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {upcomingMeetings.map((meeting, index) => (
              <motion.div
                key={meeting.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                className="bg-white p-6 rounded-xl border-2 border-border hover:border-primary transition-all"
              >
                <h3 className="text-lg font-bold text-foreground mb-3">{meeting.title}</h3>
                <div className="space-y-2 text-sm mb-4">
                  <div className="flex items-center gap-2 text-secondary">
                    <Calendar className="w-4 h-4" />
                    {format(new Date(meeting.scheduled_at), 'PPP')}
                  </div>
                  <div className="flex items-center gap-2 text-secondary">
                    <Clock className="w-4 h-4" />
                    {format(new Date(meeting.scheduled_at), 'p')} ({meeting.duration} min)
                  </div>
                  {meeting.meeting_link && (
                    <div className="flex items-center gap-2">
                      <Video className="w-4 h-4 text-primary" />
                      <a
                        href={meeting.meeting_link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary hover:underline text-xs truncate"
                      >
                        Join Meeting
                      </a>
                      <button
                        onClick={() => copyMeetingLink(meeting.meeting_link)}
                        className="p-1 hover:bg-slate-100 rounded transition-colors"
                      >
                        <Copy className="w-3 h-3" />
                      </button>
                    </div>
                  )}
                </div>
                {meeting.notes && (
                  <p className="text-xs text-secondary bg-slate-50 p-2 rounded">{meeting.notes}</p>
                )}
              </motion.div>
            ))}
            {upcomingMeetings.length === 0 && (
              <div className="col-span-full text-center py-12 bg-slate-50 rounded-xl">
                <Calendar className="w-16 h-16 text-secondary mx-auto mb-3" />
                <p className="text-lg text-secondary">No upcoming meetings</p>
              </div>
            )}
          </div>
        </div>

        {/* Quick Scheduler Modal */}
        {showQuickScheduler && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="bg-white rounded-xl p-8 max-w-2xl w-full max-h-[90vh] overflow-y-auto"
            >
              <h3 className="text-3xl font-bold text-foreground mb-6">Quick Schedule Meeting</h3>

              {/* Meeting Type Selector */}
              <div className="grid grid-cols-3 gap-3 mb-6">
                {[
                  { type: 'team', label: 'Team Meeting', icon: Users },
                  { type: 'lead', label: 'Lead Meeting', icon: Calendar },
                  { type: 'external', label: 'External', icon: Video }
                ].map((option) => {
                  const Icon = option.icon;
                  return (
                    <button
                      key={option.type}
                      onClick={() => setQuickForm({...quickForm, type: option.type})}
                      className={`p-4 rounded-lg border-2 transition-all ${
                        quickForm.type === option.type
                          ? 'border-primary bg-primary/5'
                          : 'border-border hover:border-primary/50'
                      }`}
                    >
                      <Icon className="w-6 h-6 mx-auto mb-2 text-primary" />
                      <p className="text-sm font-medium">{option.label}</p>
                    </button>
                  );
                })}
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Meeting Title *</label>
                  <input
                    type="text"
                    value={quickForm.title}
                    onChange={(e) => setQuickForm({...quickForm, title: e.target.value})}
                    placeholder="e.g., Product Demo, Team Sync"
                    className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>

                {quickForm.type === 'lead' && (
                  <div>
                    <label className="block text-sm font-medium mb-2">Select Lead</label>
                    <div className="relative">
                      <Search className="absolute left-3 top-3 w-5 h-5 text-secondary" />
                      <input
                        type="text"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        placeholder="Search leads..."
                        className="w-full pl-10 pr-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary mb-2"
                      />
                    </div>
                    <div className="max-h-40 overflow-y-auto border border-border rounded-lg">
                      {filteredLeads.slice(0, 5).map((lead) => (
                        <button
                          key={lead.id}
                          onClick={() => setQuickForm({...quickForm, lead_id: lead.id})}
                          className={`w-full text-left p-3 hover:bg-slate-50 transition-colors ${
                            quickForm.lead_id === lead.id ? 'bg-primary/10' : ''
                          }`}
                        >
                          <p className="font-medium text-sm">{lead.first_name} {lead.last_name}</p>
                          <p className="text-xs text-secondary">{lead.company}</p>
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">Date & Time *</label>
                    <input
                      type="datetime-local"
                      value={quickForm.scheduled_at}
                      onChange={(e) => setQuickForm({...quickForm, scheduled_at: e.target.value})}
                      className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">Duration</label>
                    <select
                      value={quickForm.duration}
                      onChange={(e) => setQuickForm({...quickForm, duration: parseInt(e.target.value)})}
                      className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                    >
                      <option value={15}>15 minutes</option>
                      <option value={30}>30 minutes</option>
                      <option value={60}>1 hour</option>
                      <option value={90}>1.5 hours</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Meeting Link (optional)</label>
                  <input
                    type="url"
                    value={quickForm.meeting_link}
                    onChange={(e) => setQuickForm({...quickForm, meeting_link: e.target.value})}
                    placeholder="Zoom, Google Meet, or leave blank for auto-generate"
                    className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>

                {quickForm.type === 'team' && (
                  <div>
                    <label className="block text-sm font-medium mb-2">Invite Team ({quickForm.attendees.length} selected)</label>
                    <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto border border-border rounded-lg p-3">
                      {teamMembers.filter(m => m.id !== user?.id).map((member) => (
                        <button
                          key={member.id}
                          type="button"
                          onClick={() => toggleAttendee(member)}
                          className={`flex items-center gap-2 p-2 rounded-lg border-2 transition-all ${
                            quickForm.attendees.find(a => a.id === member.id)
                              ? 'border-primary bg-primary/5'
                              : 'border-border hover:border-primary/50'
                          }`}
                        >
                          <div className="w-6 h-6 bg-gradient-to-br from-primary to-accent rounded-full flex items-center justify-center text-white text-xs">
                            {member.full_name.charAt(0)}
                          </div>
                          <span className="text-xs font-medium truncate">{member.full_name}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowQuickScheduler(false)}
                  className="flex-1 py-3 border-2 border-border rounded-lg font-semibold hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleQuickSchedule}
                  className="flex-1 py-3 bg-primary text-white rounded-lg font-semibold hover:bg-primary/90 transition-all"
                >
                  Schedule Meeting
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
};

export default MeetingsPage;