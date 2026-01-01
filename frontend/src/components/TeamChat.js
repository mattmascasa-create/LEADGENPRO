import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { MessageSquare, X, Send, Hash, User, Users, Calendar, Paperclip, Video, Phone, Search, Plus, MoreVertical } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { toast } from 'react-toastify';
import { format } from 'date-fns';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const TeamChat = () => {
  const { user } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [activeView, setActiveView] = useState('channels'); // channels, direct, meetings
  const [selectedChannel, setSelectedChannel] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [channels, setChannels] = useState([]);
  const [teamMembers, setTeamMembers] = useState([]);
  const [showScheduler, setShowScheduler] = useState(false);
  const [meetingForm, setMeetingForm] = useState({
    title: '',
    attendees: [],
    scheduled_at: '',
    duration: 30,
    meeting_link: ''
  });
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      fetchChannels();
      fetchTeamMembers();
    }
  }, [isOpen]);

  useEffect(() => {
    if (selectedChannel) {
      fetchMessages();
      const interval = setInterval(fetchMessages, 3000); // Poll for new messages
      return () => clearInterval(interval);
    }
  }, [selectedChannel]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const fetchChannels = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/chat/channels`);
      setChannels(response.data);
      if (response.data.length > 0 && !selectedChannel) {
        setSelectedChannel(response.data[0]);
      }
    } catch (error) {
      console.error('Failed to load channels');
    }
  };

  const fetchTeamMembers = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/users`);
      setTeamMembers(response.data);
    } catch (error) {
      console.error('Failed to load team members');
    }
  };

  const fetchMessages = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/chat/messages/${selectedChannel.id}`);
      setMessages(response.data);
    } catch (error) {
      console.error('Failed to load messages');
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim()) return;

    try {
      await axios.post(`${API_URL}/api/chat/messages`, {
        channel_id: selectedChannel.id,
        content: newMessage,
        type: 'text'
      });
      setNewMessage('');
      fetchMessages();
    } catch (error) {
      toast.error('Failed to send message');
    }
  };

  const handleScheduleMeeting = async () => {
    if (!meetingForm.title || !meetingForm.scheduled_at) {
      toast.error('Please fill in meeting details');
      return;
    }

    try {
      // Create appointment
      const response = await axios.post(`${API_URL}/api/appointments`, {
        title: meetingForm.title,
        lead_id: 'team-meeting',
        employee_id: user.id,
        scheduled_at: new Date(meetingForm.scheduled_at).toISOString(),
        duration: meetingForm.duration,
        meeting_link: meetingForm.meeting_link || `https://meet.leadgenpro.com/${Date.now()}`,
        notes: `Team meeting with: ${meetingForm.attendees.map(a => a.full_name).join(', ')}`
      });

      // Send meeting invite in chat
      await axios.post(`${API_URL}/api/chat/messages`, {
        channel_id: selectedChannel.id,
        content: `📅 **Meeting Scheduled**\n${meetingForm.title}\n🕐 ${format(new Date(meetingForm.scheduled_at), 'PPp')}\n👥 ${meetingForm.attendees.length} attendees\n🔗 ${meetingForm.meeting_link || 'Link will be generated'}`,
        type: 'meeting',
        metadata: response.data
      });

      toast.success('Meeting scheduled and invite sent!');
      setShowScheduler(false);
      setMeetingForm({ title: '', attendees: [], scheduled_at: '', duration: 30, meeting_link: '' });
      fetchMessages();
    } catch (error) {
      toast.error('Failed to schedule meeting');
    }
  };

  const toggleAttendee = (member) => {
    setMeetingForm(prev => ({
      ...prev,
      attendees: prev.attendees.find(a => a.id === member.id)
        ? prev.attendees.filter(a => a.id !== member.id)
        : [...prev.attendees, member]
    }));
  };

  return (
    <>
      {/* Floating Chat Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-24 right-6 w-14 h-14 bg-gradient-to-br from-blue-600 to-blue-800 text-white rounded-full shadow-2xl hover:scale-110 transition-transform duration-200 flex items-center justify-center z-40"
      >
        <MessageSquare className="w-6 h-6" />
      </button>

      {/* Chat Panel */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, x: 20, scale: 0.95 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 20, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className="fixed bottom-24 right-6 w-[800px] h-[600px] bg-white rounded-xl shadow-2xl border border-border overflow-hidden z-40 flex"
          >
            {/* Sidebar */}
            <div className="w-64 bg-slate-900 flex flex-col">
              <div className="p-4 border-b border-slate-800">
                <h3 className="text-white font-bold text-lg mb-4">Team Chat</h3>
                <div className="flex gap-2">
                  <button
                    onClick={() => setActiveView('channels')}
                    className={`flex-1 px-3 py-2 rounded text-sm font-medium transition-colors ${
                      activeView === 'channels' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Channels
                  </button>
                  <button
                    onClick={() => setActiveView('direct')}
                    className={`flex-1 px-3 py-2 rounded text-sm font-medium transition-colors ${
                      activeView === 'direct' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Direct
                  </button>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto p-2">
                {activeView === 'channels' && (
                  <div className="space-y-1">
                    {channels.map((channel) => (
                      <button
                        key={channel.id}
                        onClick={() => setSelectedChannel(channel)}
                        className={`w-full flex items-center gap-2 px-3 py-2 rounded text-left transition-colors ${
                          selectedChannel?.id === channel.id
                            ? 'bg-blue-600 text-white'
                            : 'text-slate-300 hover:bg-slate-800'
                        }`}
                      >
                        <Hash className="w-4 h-4" />
                        <span className="text-sm font-medium">{channel.name}</span>
                      </button>
                    ))}
                  </div>
                )}

                {activeView === 'direct' && (
                  <div className="space-y-1">
                    {teamMembers.filter(m => m.id !== user?.id).map((member) => (
                      <button
                        key={member.id}
                        className="w-full flex items-center gap-2 px-3 py-2 rounded text-left text-slate-300 hover:bg-slate-800 transition-colors"
                      >
                        <div className="w-8 h-8 bg-gradient-to-br from-primary to-accent rounded-full flex items-center justify-center text-white text-xs font-semibold">
                          {member.full_name.charAt(0)}
                        </div>
                        <span className="text-sm">{member.full_name}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Main Chat Area */}
            <div className="flex-1 flex flex-col">
              {/* Header */}
              <div className="p-4 border-b border-border flex items-center justify-between bg-white">
                <div className="flex items-center gap-3">
                  <Hash className="w-5 h-5 text-secondary" />
                  <h4 className="font-bold text-foreground">{selectedChannel?.name || 'Select a channel'}</h4>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setShowScheduler(true)}
                    className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
                    title="Schedule Meeting"
                  >
                    <Calendar className="w-5 h-5 text-secondary" />
                  </button>
                  <button
                    onClick={() => window.open('https://meet.google.com/new', '_blank')}
                    className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
                    title="Start Video Call"
                  >
                    <Video className="w-5 h-5 text-secondary" />
                  </button>
                  <button
                    onClick={() => setIsOpen(false)}
                    className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
                  >
                    <X className="w-5 h-5 text-secondary" />
                  </button>
                </div>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50">
                {messages.map((msg, index) => (
                  <div key={index} className="flex gap-3">
                    <div className="w-8 h-8 bg-gradient-to-br from-primary to-accent rounded-full flex items-center justify-center text-white text-xs font-semibold flex-shrink-0">
                      {msg.sender_name?.charAt(0) || 'U'}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-semibold text-sm text-foreground">{msg.sender_name}</span>
                        <span className="text-xs text-secondary">{format(new Date(msg.created_at), 'p')}</span>
                      </div>
                      <div className="text-sm text-foreground whitespace-pre-wrap">{msg.content}</div>
                      {msg.type === 'meeting' && (
                        <div className="mt-2 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                          <p className="text-sm font-semibold text-blue-900">Meeting Invite</p>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>

              {/* Input */}
              <form onSubmit={handleSendMessage} className="p-4 border-t border-border bg-white">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    placeholder="Type a message..."
                    className="flex-1 px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                  <button
                    type="button"
                    className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
                    title="Attach File"
                  >
                    <Paperclip className="w-5 h-5 text-secondary" />
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 bg-primary text-white rounded-lg font-medium hover:bg-primary/90 transition-colors"
                  >
                    <Send className="w-5 h-5" />
                  </button>
                </div>
              </form>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Meeting Scheduler Modal */}
      <AnimatePresence>
        {showScheduler && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-white rounded-xl p-8 max-w-2xl w-full max-h-[90vh] overflow-y-auto"
            >
              <h3 className="text-2xl font-bold text-foreground mb-6">Schedule Team Meeting</h3>

              <div className="space-y-4 mb-6">
                <div>
                  <label className="block text-sm font-medium mb-2">Meeting Title</label>
                  <input
                    type="text"
                    value={meetingForm.title}
                    onChange={(e) => setMeetingForm({...meetingForm, title: e.target.value})}
                    placeholder="e.g., Daily Standup"
                    className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>

                <div className="grid md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">Date & Time</label>
                    <input
                      type="datetime-local"
                      value={meetingForm.scheduled_at}
                      onChange={(e) => setMeetingForm({...meetingForm, scheduled_at: e.target.value})}
                      className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">Duration (minutes)</label>
                    <select
                      value={meetingForm.duration}
                      onChange={(e) => setMeetingForm({...meetingForm, duration: parseInt(e.target.value)})}
                      className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                    >
                      <option value={15}>15 min</option>
                      <option value={30}>30 min</option>
                      <option value={60}>1 hour</option>
                      <option value={90}>1.5 hours</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Meeting Link (optional)</label>
                  <input
                    type="url"
                    value={meetingForm.meeting_link}
                    onChange={(e) => setMeetingForm({...meetingForm, meeting_link: e.target.value})}
                    placeholder="https://zoom.us/j/... or leave blank for auto-generated"
                    className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-3">Invite Team Members ({meetingForm.attendees.length} selected)</label>
                  <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto border border-border rounded-lg p-3">
                    {teamMembers.filter(m => m.id !== user?.id).map((member) => (
                      <button
                        key={member.id}
                        type="button"
                        onClick={() => toggleAttendee(member)}
                        className={`flex items-center gap-2 p-2 rounded-lg border-2 transition-all ${
                          meetingForm.attendees.find(a => a.id === member.id)
                            ? 'border-primary bg-primary/5'
                            : 'border-border hover:border-primary/50'
                        }`}
                      >
                        <div className="w-8 h-8 bg-gradient-to-br from-primary to-accent rounded-full flex items-center justify-center text-white text-xs font-semibold">
                          {member.full_name.charAt(0)}
                        </div>
                        <span className="text-sm font-medium">{member.full_name}</span>
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => setShowScheduler(false)}
                  className="flex-1 py-3 border-2 border-border rounded-lg font-semibold hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleScheduleMeeting}
                  className="flex-1 py-3 bg-primary text-white rounded-lg font-semibold hover:bg-primary/90 transition-all"
                >
                  Schedule Meeting
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </>
  );
};

export default TeamChat;