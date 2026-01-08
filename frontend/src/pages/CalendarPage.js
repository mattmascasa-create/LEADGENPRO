import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Calendar, dateFnsLocalizer } from 'react-big-calendar';
import { format, parse, startOfWeek, getDay, addHours } from 'date-fns';
import enUS from 'date-fns/locale/en-US';
import { 
  Plus, X, Clock, User, Users, MapPin, Video, Phone,
  CalendarDays, ChevronLeft, ChevronRight, Trash2, Edit,
  ExternalLink, Download, Copy, Check
} from 'lucide-react';
import { toast } from 'react-toastify';
import { motion, AnimatePresence } from 'framer-motion';
import DashboardLayout from '@/components/DashboardLayout';
import 'react-big-calendar/lib/css/react-big-calendar.css';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Google Meet icon SVG
const GoogleMeetIcon = () => (
  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none">
    <path d="M12 12H3V18.5C3 19.33 3.67 20 4.5 20H12V12Z" fill="#00832d"/>
    <path d="M12 4H4.5C3.67 4 3 4.67 3 5.5V12H12V4Z" fill="#0066da"/>
    <path d="M21 6.5V17.5L16 13V11L21 6.5Z" fill="#e94235"/>
    <path d="M12 12V20H19.5C20.33 20 21 19.33 21 18.5V17.5L16 13H12V12Z" fill="#2684fc"/>
    <path d="M12 4V12H16L21 6.5V5.5C21 4.67 20.33 4 19.5 4H12Z" fill="#00ac47"/>
  </svg>
);

// Google Calendar icon SVG
const GoogleCalendarIcon = () => (
  <svg className="w-5 h-5" viewBox="0 0 24 24">
    <path fill="#4285F4" d="M22 6v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2h16c1.1 0 2 .9 2 2z"/>
    <path fill="#fff" d="M4 8v10h16V8H4z"/>
    <path fill="#EA4335" d="M10 13h4v4h-4z"/>
    <path fill="#FBBC05" d="M10 9h4v4h-4z"/>
    <path fill="#34A853" d="M6 13h4v4H6z"/>
    <path fill="#4285F4" d="M14 13h4v4h-4z"/>
  </svg>
);

const locales = { 'en-US': enUS };
const localizer = dateFnsLocalizer({
  format,
  parse,
  startOfWeek,
  getDay,
  locales
});

const eventStyleGetter = (event) => {
  const colors = {
    meeting: { bg: '#3b82f6', border: '#2563eb' },
    call: { bg: '#10b981', border: '#059669' },
    task: { bg: '#f59e0b', border: '#d97706' },
    reminder: { bg: '#8b5cf6', border: '#7c3aed' },
    other: { bg: '#6b7280', border: '#4b5563' }
  };
  const color = colors[event.type] || colors.other;
  return {
    style: {
      backgroundColor: color.bg,
      borderLeft: `4px solid ${color.border}`,
      borderRadius: '4px',
      color: 'white',
      padding: '2px 8px'
    }
  };
};

const CalendarPage = () => {
  const [events, setEvents] = useState([]);
  const [teamMembers, setTeamMembers] = useState([]);
  const [showEventModal, setShowEventModal] = useState(false);
  const [showEventDetail, setShowEventDetail] = useState(null);
  const [selectedSlot, setSelectedSlot] = useState(null);
  const [currentDate, setCurrentDate] = useState(new Date());
  const [view, setView] = useState('month');
  const [addMeetLink, setAddMeetLink] = useState(false);
  const [copiedLink, setCopiedLink] = useState(false);
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    type: 'meeting',
    start: '',
    end: '',
    attendees: [],
    location: '',
    meeting_link: ''
  });

  useEffect(() => {
    fetchEvents();
    fetchTeamMembers();
  }, []);

  const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return { headers: { Authorization: `Bearer ${token}` } };
  };

  const fetchEvents = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/calendar/events`, getAuthHeaders());
      const formattedEvents = response.data.map(event => ({
        ...event,
        start: new Date(event.start),
        end: new Date(event.end)
      }));
      setEvents(formattedEvents);
    } catch (error) {
      console.error('Failed to load events:', error);
    }
  };

  const fetchTeamMembers = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/team-members`, getAuthHeaders());
      setTeamMembers(response.data);
    } catch (error) {
      console.error('Failed to load team members:', error);
    }
  };

  const handleSelectSlot = useCallback(({ start, end }) => {
    setSelectedSlot({ start, end });
    setFormData({
      ...formData,
      start: format(start, "yyyy-MM-dd'T'HH:mm"),
      end: format(end, "yyyy-MM-dd'T'HH:mm")
    });
    setShowEventModal(true);
  }, [formData]);

  const handleSelectEvent = useCallback((event) => {
    setShowEventDetail(event);
  }, []);

  const handleCreateEvent = async (e) => {
    e.preventDefault();
    try {
      // Use the endpoint with Meet link if checkbox is checked
      const endpoint = addMeetLink ? '/api/calendar/events/with-meet' : '/api/calendar/events';
      
      const response = await axios.post(`${API_URL}${endpoint}`, {
        ...formData,
        start: new Date(formData.start).toISOString(),
        end: new Date(formData.end).toISOString()
      }, getAuthHeaders());
      
      if (addMeetLink && response.data.meeting_link) {
        toast.success(`Event created with Google Meet link!`);
      } else {
        toast.success('Event created!');
      }
      
      setShowEventModal(false);
      setAddMeetLink(false);
      setFormData({
        title: '',
        description: '',
        type: 'meeting',
        start: '',
        end: '',
        attendees: [],
        location: '',
        meeting_link: ''
      });
      fetchEvents();
    } catch (error) {
      toast.error('Failed to create event');
    }
  };

  const handleDeleteEvent = async (eventId) => {
    try {
      await axios.delete(`${API_URL}/api/calendar/events/${eventId}`, getAuthHeaders());
      toast.success('Event deleted!');
      setShowEventDetail(null);
      fetchEvents();
    } catch (error) {
      toast.error('Failed to delete event');
    }
  };

  const handleAddMeetToEvent = async (eventId) => {
    try {
      const response = await axios.post(`${API_URL}/api/calendar/events/${eventId}/add-meet`, {}, getAuthHeaders());
      toast.success('Google Meet link added!');
      setShowEventDetail({...showEventDetail, meeting_link: response.data.meeting_link});
      fetchEvents();
    } catch (error) {
      toast.error('Failed to add Meet link');
    }
  };

  const handleExportToGoogleCalendar = async (eventId) => {
    try {
      const response = await axios.get(`${API_URL}/api/calendar/export/google-url/${eventId}`, getAuthHeaders());
      window.open(response.data.google_calendar_url, '_blank');
    } catch (error) {
      toast.error('Failed to export to Google Calendar');
    }
  };

  const handleDownloadICS = async (eventId) => {
    try {
      window.open(`${API_URL}/api/calendar/export/ics/${eventId}`, '_blank');
      toast.success('ICS file downloading...');
    } catch (error) {
      toast.error('Failed to download ICS file');
    }
  };

  const copyMeetLink = (link) => {
    navigator.clipboard.writeText(link);
    setCopiedLink(true);
    toast.success('Meeting link copied!');
    setTimeout(() => setCopiedLink(false), 2000);
  };

  const eventTypes = [
    { value: 'meeting', label: 'Meeting', icon: Video },
    { value: 'call', label: 'Call', icon: Phone },
    { value: 'task', label: 'Task', icon: CalendarDays },
    { value: 'reminder', label: 'Reminder', icon: Clock }
  ];

  return (
    <DashboardLayout>
      <div>
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-4xl font-bold text-foreground mb-2">Team Calendar</h1>
            <p className="text-secondary">Manage team schedules and events</p>
          </div>
          <button
            onClick={() => {
              setFormData({
                ...formData,
                start: format(new Date(), "yyyy-MM-dd'T'HH:mm"),
                end: format(addHours(new Date(), 1), "yyyy-MM-dd'T'HH:mm")
              });
              setShowEventModal(true);
            }}
            className="px-4 py-2 bg-primary text-white rounded-lg font-medium hover:bg-primary/90 flex items-center gap-2"
          >
            <Plus className="w-5 h-5" />
            New Event
          </button>
        </div>

        {/* Calendar */}
        <div className="bg-white rounded-xl border border-border p-4" style={{ height: 700 }}>
          <Calendar
            localizer={localizer}
            events={events}
            startAccessor="start"
            endAccessor="end"
            style={{ height: '100%' }}
            onSelectEvent={handleSelectEvent}
            onSelectSlot={handleSelectSlot}
            selectable
            eventPropGetter={eventStyleGetter}
            date={currentDate}
            onNavigate={setCurrentDate}
            view={view}
            onView={setView}
            views={['month', 'week', 'day', 'agenda']}
            popup
            components={{
              toolbar: (props) => (
                <div className="flex items-center justify-between mb-4 pb-4 border-b border-border">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => props.onNavigate('PREV')}
                      className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
                    >
                      <ChevronLeft className="w-5 h-5" />
                    </button>
                    <button
                      onClick={() => props.onNavigate('TODAY')}
                      className="px-3 py-1 text-sm font-medium hover:bg-slate-100 rounded-lg transition-colors"
                    >
                      Today
                    </button>
                    <button
                      onClick={() => props.onNavigate('NEXT')}
                      className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
                    >
                      <ChevronRight className="w-5 h-5" />
                    </button>
                    <span className="text-lg font-semibold text-foreground ml-4">
                      {props.label}
                    </span>
                  </div>
                  <div className="flex gap-1 bg-slate-100 p-1 rounded-lg">
                    {['month', 'week', 'day', 'agenda'].map((v) => (
                      <button
                        key={v}
                        onClick={() => props.onView(v)}
                        className={`px-3 py-1 text-sm font-medium rounded-md capitalize transition-colors ${
                          props.view === v ? 'bg-white shadow-sm' : 'hover:bg-white/50'
                        }`}
                      >
                        {v}
                      </button>
                    ))}
                  </div>
                </div>
              )
            }}
          />
        </div>

        {/* Create Event Modal */}
        <AnimatePresence>
          {showEventModal && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
              onClick={(e) => e.target === e.currentTarget && setShowEventModal(false)}
            >
              <motion.div
                initial={{ scale: 0.95 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0.95 }}
                className="bg-white rounded-xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden"
              >
                <div className="p-6 border-b border-border flex items-center justify-between">
                  <h2 className="text-xl font-bold">Create Event</h2>
                  <button onClick={() => setShowEventModal(false)} className="p-1 hover:bg-slate-100 rounded">
                    <X className="w-5 h-5" />
                  </button>
                </div>
                <form onSubmit={handleCreateEvent} className="p-6 space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">Event Title *</label>
                    <input
                      type="text"
                      value={formData.title}
                      onChange={(e) => setFormData({...formData, title: e.target.value})}
                      required
                      className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                      placeholder="Enter event title"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Event Type</label>
                    <div className="grid grid-cols-4 gap-2">
                      {eventTypes.map((type) => {
                        const Icon = type.icon;
                        return (
                          <button
                            key={type.value}
                            type="button"
                            onClick={() => setFormData({...formData, type: type.value})}
                            className={`p-2 rounded-lg border-2 flex flex-col items-center gap-1 transition-all ${
                              formData.type === type.value
                                ? 'border-primary bg-primary/5'
                                : 'border-border hover:border-primary/50'
                            }`}
                          >
                            <Icon className="w-5 h-5" />
                            <span className="text-xs">{type.label}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium mb-1">Start *</label>
                      <input
                        type="datetime-local"
                        value={formData.start}
                        onChange={(e) => setFormData({...formData, start: e.target.value})}
                        required
                        className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">End *</label>
                      <input
                        type="datetime-local"
                        value={formData.end}
                        onChange={(e) => setFormData({...formData, end: e.target.value})}
                        required
                        className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Description</label>
                    <textarea
                      value={formData.description}
                      onChange={(e) => setFormData({...formData, description: e.target.value})}
                      className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary resize-none"
                      rows={3}
                      placeholder="Add event description..."
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Location</label>
                    <input
                      type="text"
                      value={formData.location}
                      onChange={(e) => setFormData({...formData, location: e.target.value})}
                      className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                      placeholder="Add location or meeting room"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Meeting Link</label>
                    <input
                      type="url"
                      value={formData.meeting_link}
                      onChange={(e) => setFormData({...formData, meeting_link: e.target.value})}
                      className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                      placeholder="https://zoom.us/j/..."
                      disabled={addMeetLink}
                    />
                    {/* Auto-generate Google Meet Link checkbox */}
                    <label className="flex items-center gap-2 mt-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={addMeetLink}
                        onChange={(e) => {
                          setAddMeetLink(e.target.checked);
                          if (e.target.checked) {
                            setFormData({...formData, meeting_link: ''});
                          }
                        }}
                        className="w-4 h-4 rounded border-border text-primary focus:ring-primary"
                      />
                      <span className="flex items-center gap-2 text-sm">
                        <GoogleMeetIcon />
                        Auto-generate Google Meet link
                      </span>
                    </label>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Attendees</label>
                    <select
                      multiple
                      value={formData.attendees}
                      onChange={(e) => setFormData({
                        ...formData,
                        attendees: Array.from(e.target.selectedOptions, option => option.value)
                      })}
                      className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                    >
                      {teamMembers.map((member) => (
                        <option key={member.id} value={member.id}>
                          {member.full_name}
                        </option>
                      ))}
                    </select>
                    <p className="text-xs text-secondary mt-1">Hold Ctrl/Cmd to select multiple</p>
                  </div>
                  <div className="flex gap-3 pt-4">
                    <button
                      type="button"
                      onClick={() => setShowEventModal(false)}
                      className="flex-1 py-2 border border-border rounded-lg font-medium hover:bg-slate-50"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="flex-1 py-2 bg-primary text-white rounded-lg font-medium hover:bg-primary/90"
                    >
                      Create Event
                    </button>
                  </div>
                </form>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Event Detail Modal */}
        <AnimatePresence>
          {showEventDetail && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
              onClick={(e) => e.target === e.currentTarget && setShowEventDetail(null)}
            >
              <motion.div
                initial={{ scale: 0.95 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0.95 }}
                className="bg-white rounded-xl shadow-2xl w-full max-w-md mx-4 overflow-hidden"
              >
                <div className={`p-6 text-white ${
                  showEventDetail.type === 'meeting' ? 'bg-blue-500' :
                  showEventDetail.type === 'call' ? 'bg-green-500' :
                  showEventDetail.type === 'task' ? 'bg-yellow-500' :
                  'bg-purple-500'
                }`}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium uppercase opacity-80">{showEventDetail.type}</span>
                    <button onClick={() => setShowEventDetail(null)} className="p-1 hover:bg-white/20 rounded">
                      <X className="w-5 h-5" />
                    </button>
                  </div>
                  <h2 className="text-2xl font-bold">{showEventDetail.title}</h2>
                </div>
                <div className="p-6 space-y-4">
                  <div className="flex items-center gap-3 text-secondary">
                    <Clock className="w-5 h-5" />
                    <div>
                      <p className="font-medium text-foreground">
                        {format(showEventDetail.start, 'EEEE, MMMM d, yyyy')}
                      </p>
                      <p className="text-sm">
                        {format(showEventDetail.start, 'h:mm a')} - {format(showEventDetail.end, 'h:mm a')}
                      </p>
                    </div>
                  </div>
                  {showEventDetail.location && (
                    <div className="flex items-center gap-3 text-secondary">
                      <MapPin className="w-5 h-5" />
                      <span>{showEventDetail.location}</span>
                    </div>
                  )}
                  {showEventDetail.meeting_link && (
                    <div className="flex items-center gap-3">
                      <Video className="w-5 h-5 text-secondary" />
                      <a
                        href={showEventDetail.meeting_link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary hover:underline flex items-center gap-1"
                      >
                        <GoogleMeetIcon />
                        Join Meeting
                        <ExternalLink className="w-3 h-3" />
                      </a>
                      <button
                        onClick={() => copyMeetLink(showEventDetail.meeting_link)}
                        className="p-1 hover:bg-slate-100 rounded"
                        title="Copy link"
                      >
                        {copiedLink ? <Check className="w-4 h-4 text-green-600" /> : <Copy className="w-4 h-4 text-secondary" />}
                      </button>
                    </div>
                  )}
                  {!showEventDetail.meeting_link && showEventDetail.type === 'meeting' && (
                    <button
                      onClick={() => handleAddMeetToEvent(showEventDetail.id)}
                      className="flex items-center gap-2 px-3 py-2 bg-green-50 text-green-700 rounded-lg hover:bg-green-100 transition-colors text-sm font-medium"
                    >
                      <GoogleMeetIcon />
                      Add Google Meet Link
                    </button>
                  )}
                  {showEventDetail.description && (
                    <div className="pt-4 border-t border-border">
                      <p className="text-sm text-secondary">{showEventDetail.description}</p>
                    </div>
                  )}
                  {showEventDetail.attendees && showEventDetail.attendees.length > 0 && (
                    <div className="pt-4 border-t border-border">
                      <p className="text-sm font-medium mb-2 flex items-center gap-2">
                        <Users className="w-4 h-4" />
                        Attendees
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {showEventDetail.attendee_names?.map((name, idx) => (
                          <span key={idx} className="px-2 py-1 bg-slate-100 rounded text-sm">
                            {name}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  <div className="flex gap-3 pt-4">
                    <button
                      onClick={() => handleDeleteEvent(showEventDetail.id)}
                      className="flex-1 py-2 border border-red-200 text-red-600 rounded-lg font-medium hover:bg-red-50 flex items-center justify-center gap-2"
                    >
                      <Trash2 className="w-4 h-4" />
                      Delete
                    </button>
                    <button
                      onClick={() => setShowEventDetail(null)}
                      className="flex-1 py-2 bg-primary text-white rounded-lg font-medium hover:bg-primary/90"
                    >
                      Close
                    </button>
                  </div>
                  
                  {/* Google Calendar Export Options */}
                  <div className="pt-4 border-t border-border">
                    <p className="text-sm font-medium text-secondary mb-3">Export to Calendar</p>
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleExportToGoogleCalendar(showEventDetail.id)}
                        className="flex-1 py-2 px-3 border border-border rounded-lg text-sm font-medium hover:bg-slate-50 flex items-center justify-center gap-2"
                      >
                        <GoogleCalendarIcon />
                        Add to Google Calendar
                      </button>
                      <button
                        onClick={() => handleDownloadICS(showEventDetail.id)}
                        className="py-2 px-3 border border-border rounded-lg text-sm font-medium hover:bg-slate-50 flex items-center justify-center gap-2"
                        title="Download ICS file"
                      >
                        <Download className="w-4 h-4" />
                        ICS
                      </button>
                    </div>
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

export default CalendarPage;
