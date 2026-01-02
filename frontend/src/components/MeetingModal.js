import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Calendar, X, Clock, User, Users, MapPin, Video, Link as LinkIcon
} from 'lucide-react';
import { toast } from 'react-toastify';
import { format, addHours } from 'date-fns';
import { motion, AnimatePresence } from 'framer-motion';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const MeetingModal = ({ isOpen, onClose, lead, onMeetingScheduled }) => {
  const [teamMembers, setTeamMembers] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    type: 'meeting',
    start: '',
    end: '',
    location: '',
    meeting_link: '',
    visibility: 'public', // public or private
    assignee: '' // specific team member ID
  });

  useEffect(() => {
    if (isOpen) {
      fetchTeamMembers();
      // Set default times
      const now = new Date();
      const start = addHours(now, 1);
      const end = addHours(now, 2);
      setFormData(prev => ({
        ...prev,
        title: lead ? `Meeting with ${lead.first_name} ${lead.last_name}` : 'New Meeting',
        start: format(start, "yyyy-MM-dd'T'HH:mm"),
        end: format(end, "yyyy-MM-dd'T'HH:mm"),
        description: lead ? `Meeting scheduled with ${lead.first_name} ${lead.last_name} from ${lead.company}` : ''
      }));
    }
  }, [isOpen, lead]);

  const fetchTeamMembers = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/users`);
      setTeamMembers(response.data);
    } catch (error) {
      console.error('Failed to load team members:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.title || !formData.start || !formData.end) {
      toast.error('Please fill in all required fields');
      return;
    }

    setIsSubmitting(true);

    try {
      // Build attendees list
      const attendees = [];
      if (formData.visibility === 'private' && formData.assignee) {
        attendees.push(formData.assignee);
      }

      const eventData = {
        title: formData.title,
        description: formData.description,
        type: formData.type,
        start: new Date(formData.start).toISOString(),
        end: new Date(formData.end).toISOString(),
        location: formData.location,
        meeting_link: formData.meeting_link,
        attendees: attendees
      };

      await axios.post(`${API_URL}/api/calendar/events`, eventData);

      // Log activity if lead is associated
      if (lead) {
        await axios.post(`${API_URL}/api/activities`, {
          type: 'meeting_scheduled',
          description: `Scheduled meeting: ${formData.title}`,
          lead_id: lead.id,
          metadata: {
            meeting_title: formData.title,
            meeting_time: formData.start
          }
        });
      }

      toast.success('Meeting scheduled successfully!');
      
      if (onMeetingScheduled) {
        onMeetingScheduled();
      }
      
      onClose();
    } catch (error) {
      console.error('Error scheduling meeting:', error);
      toast.error('Failed to schedule meeting');
    } finally {
      setIsSubmitting(false);
    }
  };

  const meetingTypes = [
    { value: 'meeting', label: 'In-Person Meeting', icon: Users },
    { value: 'call', label: 'Phone Call', icon: User },
    { value: 'video', label: 'Video Call', icon: Video }
  ];

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
        onClick={(e) => e.target === e.currentTarget && onClose()}
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          className="bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden max-h-[90vh] overflow-y-auto"
        >
          {/* Header */}
          <div className="bg-purple-500 p-6 text-white">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-xl font-bold flex items-center gap-2">
                <Calendar className="w-6 h-6" />
                Schedule Meeting
              </h2>
              <button onClick={onClose} className="p-1 hover:bg-white/20 rounded-full transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>
            {lead && (
              <p className="text-white/80">
                with {lead.first_name} {lead.last_name} • {lead.company}
              </p>
            )}
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="p-6 space-y-4">
            {/* Title */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Meeting Title *</label>
              <input
                type="text"
                value={formData.title}
                onChange={(e) => setFormData({...formData, title: e.target.value})}
                required
                className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                placeholder="Enter meeting title"
              />
            </div>

            {/* Meeting Type */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">Meeting Type</label>
              <div className="grid grid-cols-3 gap-2">
                {meetingTypes.map((type) => {
                  const Icon = type.icon;
                  return (
                    <button
                      key={type.value}
                      type="button"
                      onClick={() => setFormData({...formData, type: type.value})}
                      className={`p-3 rounded-lg border-2 flex flex-col items-center gap-1 transition-all ${
                        formData.type === type.value
                          ? 'border-purple-500 bg-purple-50'
                          : 'border-border hover:border-purple-300'
                      }`}
                    >
                      <Icon className="w-5 h-5" />
                      <span className="text-xs font-medium">{type.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Date/Time */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Start *</label>
                <input
                  type="datetime-local"
                  value={formData.start}
                  onChange={(e) => setFormData({...formData, start: e.target.value})}
                  required
                  className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">End *</label>
                <input
                  type="datetime-local"
                  value={formData.end}
                  onChange={(e) => setFormData({...formData, end: e.target.value})}
                  required
                  className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>
            </div>

            {/* Visibility */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">Visibility</label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setFormData({...formData, visibility: 'public', assignee: ''})}
                  className={`p-3 rounded-lg border-2 flex items-center justify-center gap-2 transition-all ${
                    formData.visibility === 'public'
                      ? 'border-purple-500 bg-purple-50'
                      : 'border-border hover:border-purple-300'
                  }`}
                >
                  <Users className="w-4 h-4" />
                  <span className="text-sm font-medium">Public (All Team)</span>
                </button>
                <button
                  type="button"
                  onClick={() => setFormData({...formData, visibility: 'private'})}
                  className={`p-3 rounded-lg border-2 flex items-center justify-center gap-2 transition-all ${
                    formData.visibility === 'private'
                      ? 'border-purple-500 bg-purple-50'
                      : 'border-border hover:border-purple-300'
                  }`}
                >
                  <User className="w-4 h-4" />
                  <span className="text-sm font-medium">Assign to Person</span>
                </button>
              </div>
            </div>

            {/* Assignee (if private) */}
            {formData.visibility === 'private' && (
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Assign To</label>
                <select
                  value={formData.assignee}
                  onChange={(e) => setFormData({...formData, assignee: e.target.value})}
                  className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                >
                  <option value="">Select team member...</option>
                  {teamMembers.map((member) => (
                    <option key={member.id} value={member.id}>
                      {member.full_name}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Location */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">
                <MapPin className="w-4 h-4 inline mr-1" />
                Location
              </label>
              <input
                type="text"
                value={formData.location}
                onChange={(e) => setFormData({...formData, location: e.target.value})}
                className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                placeholder="Conference Room A, Office Address, etc."
              />
            </div>

            {/* Meeting Link */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">
                <LinkIcon className="w-4 h-4 inline mr-1" />
                Meeting Link
              </label>
              <input
                type="url"
                value={formData.meeting_link}
                onChange={(e) => setFormData({...formData, meeting_link: e.target.value})}
                className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                placeholder="https://zoom.us/j/..."
              />
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Notes</label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({...formData, description: e.target.value})}
                rows={3}
                className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none"
                placeholder="Add meeting agenda or notes..."
              />
            </div>

            {/* Actions */}
            <div className="flex gap-3 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 py-3 border border-border rounded-xl font-medium hover:bg-slate-50 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="flex-1 py-3 bg-purple-500 text-white rounded-xl font-semibold hover:bg-purple-600 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
              >
                <Calendar className="w-4 h-4" />
                {isSubmitting ? 'Scheduling...' : 'Schedule Meeting'}
              </button>
            </div>
          </form>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default MeetingModal;
