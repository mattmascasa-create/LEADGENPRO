import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  MessageSquare, X, Send, Hash, User, Users, Calendar, 
  Paperclip, Video, Phone, Search, Plus, MoreVertical,
  AtSign, Reply, Check, CheckCheck, Image, File, Link2,
  Clock, CalendarDays, ExternalLink, ChevronDown, ChevronRight,
  Smile, ThumbsUp, Heart, Star, Bookmark, Coffee, Home,
  Plane, Thermometer, Target, Car, Bell, Settings,
  Circle, Minus, Moon, BellRing, BellDot
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { toast } from 'react-toastify';
import { format, formatDistanceToNow } from 'date-fns';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Status presets with emojis
const STATUS_PRESETS = {
  online: { emoji: '🟢', text: 'Online', color: 'bg-green-500' },
  away: { emoji: '🟡', text: 'Away', color: 'bg-yellow-500' },
  busy: { emoji: '🔴', text: 'Busy', color: 'bg-red-500' },
  offline: { emoji: '⚫', text: 'Offline', color: 'bg-gray-500' },
  lunch: { emoji: '🍕', text: 'At Lunch', color: 'bg-orange-500' },
  wfh: { emoji: '🏠', text: 'Working from Home', color: 'bg-blue-500' },
  vacation: { emoji: '🏖️', text: 'On Vacation', color: 'bg-purple-500' },
  meeting: { emoji: '📅', text: 'In a Meeting', color: 'bg-blue-600' },
  sick: { emoji: '🤒', text: 'Out Sick', color: 'bg-gray-400' },
  focus: { emoji: '🎯', text: 'Focus Time', color: 'bg-red-600' },
  commuting: { emoji: '🚗', text: 'Commuting', color: 'bg-yellow-600' },
  brb: { emoji: '⏰', text: 'Be Right Back', color: 'bg-yellow-500' }
};

// Emoji picker for reactions
const REACTION_EMOJIS = ['👍', '❤️', '😄', '🎉', '🤔', '👀', '🔥', '💯', '👏', '😢'];

// Common emojis for messages
const QUICK_EMOJIS = ['😀', '😂', '🥰', '😎', '🤔', '👍', '👎', '❤️', '🎉', '🔥', '💯', '✅', '❌', '⭐', '🚀'];

const TeamChatEnhanced = () => {
  const { user } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [activeView, setActiveView] = useState('channels');
  const [selectedChannel, setSelectedChannel] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [channels, setChannels] = useState([]);
  const [teamMembers, setTeamMembers] = useState([]);
  const [userStatuses, setUserStatuses] = useState({});
  const [showScheduler, setShowScheduler] = useState(false);
  const [showMentions, setShowMentions] = useState(false);
  const [mentionSearch, setMentionSearch] = useState('');
  const [cursorPosition, setCursorPosition] = useState(0);
  const [replyingTo, setReplyingTo] = useState(null);
  const [expandedThreads, setExpandedThreads] = useState({});
  const [showAvailability, setShowAvailability] = useState(false);
  const [selectedMember, setSelectedMember] = useState(null);
  const [memberAvailability, setMemberAvailability] = useState([]);
  const [attachmentPreview, setAttachmentPreview] = useState(null);
  const [showReactions, setShowReactions] = useState(null);
  const [showEmojiPicker, setShowEmojiPicker] = useState(false);
  const [showStatusPicker, setShowStatusPicker] = useState(false);
  const [myStatus, setMyStatus] = useState({ status: 'online', status_emoji: '🟢', status_text: 'Online' });
  const [searchQuery, setSearchQuery] = useState('');
  const [showSearch, setShowSearch] = useState(false);
  const [unreadCounts, setUnreadCounts] = useState({});
  
  const [meetingForm, setMeetingForm] = useState({
    title: '',
    attendees: [],
    scheduled_at: '',
    duration: 30,
    meeting_link: ''
  });
  
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const fileInputRef = useRef(null);

  // Fetch data on mount
  useEffect(() => {
    if (isOpen) {
      fetchChannels();
      fetchTeamMembers();
      fetchUserStatuses();
      updateMyPresence();
      
      // Poll for status updates every 10 seconds
      const statusInterval = setInterval(fetchUserStatuses, 10000);
      // Update my presence every 30 seconds
      const presenceInterval = setInterval(updateMyPresence, 30000);
      
      return () => {
        clearInterval(statusInterval);
        clearInterval(presenceInterval);
      };
    }
  }, [isOpen]);

  useEffect(() => {
    if (selectedChannel) {
      fetchMessages();
      const interval = setInterval(fetchMessages, 3000);
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
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/api/chat/channels`, {
        headers: { Authorization: `Bearer ${token}` }
      });
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
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/api/users`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setTeamMembers(response.data);
    } catch (error) {
      console.error('Failed to load team members');
    }
  };

  const fetchUserStatuses = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/api/users/status`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const statusMap = {};
      response.data.forEach(s => {
        statusMap[s.user_id] = s;
      });
      setUserStatuses(statusMap);
    } catch (error) {
      console.error('Failed to load user statuses');
    }
  };

  const updateMyPresence = async () => {
    try {
      const token = localStorage.getItem('token');
      // Just update last_seen without changing status
      await axios.put(`${API_URL}/api/users/status`, {
        status: myStatus.status,
        status_emoji: myStatus.status_emoji,
        status_text: myStatus.status_text
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
    } catch (error) {
      console.error('Failed to update presence');
    }
  };

  const updateMyStatus = async (statusKey, customText = null, duration = null) => {
    try {
      const token = localStorage.getItem('token');
      const preset = STATUS_PRESETS[statusKey];
      
      const statusData = {
        status: statusKey,
        status_emoji: preset?.emoji,
        status_text: customText || preset?.text,
        duration_minutes: duration
      };
      
      const response = await axios.put(`${API_URL}/api/users/status`, statusData, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      setMyStatus(response.data);
      setShowStatusPicker(false);
      toast.success(`Status updated to ${preset?.emoji || ''} ${customText || preset?.text}`);
    } catch (error) {
      toast.error('Failed to update status');
    }
  };

  const fetchMessages = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/api/chat/messages/${selectedChannel.id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setMessages(response.data);
    } catch (error) {
      console.error('Failed to load messages');
    }
  };

  const fetchMemberAvailability = async (memberId) => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/api/booking/${memberId}/slots?days=7`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setMemberAvailability(response.data.available_slots || []);
    } catch (error) {
      console.error('Failed to fetch availability');
      setMemberAvailability([]);
    }
  };

  // Handle @mention detection
  const handleInputChange = (e) => {
    const value = e.target.value;
    const position = e.target.selectionStart;
    setNewMessage(value);
    setCursorPosition(position);

    // Detect @ mentions
    const textBeforeCursor = value.slice(0, position);
    const atIndex = textBeforeCursor.lastIndexOf('@');
    
    if (atIndex !== -1 && (atIndex === 0 || textBeforeCursor[atIndex - 1] === ' ')) {
      const searchText = textBeforeCursor.slice(atIndex + 1);
      if (!searchText.includes(' ')) {
        setMentionSearch(searchText.toLowerCase());
        setShowMentions(true);
        return;
      }
    }
    setShowMentions(false);
  };

  const insertMention = (member) => {
    const textBeforeCursor = newMessage.slice(0, cursorPosition);
    const atIndex = textBeforeCursor.lastIndexOf('@');
    const textAfterCursor = newMessage.slice(cursorPosition);
    
    const newText = textBeforeCursor.slice(0, atIndex) + `@${member.full_name} ` + textAfterCursor;
    setNewMessage(newText);
    setShowMentions(false);
    inputRef.current?.focus();
  };

  const insertEmoji = (emoji) => {
    const newText = newMessage.slice(0, cursorPosition) + emoji + newMessage.slice(cursorPosition);
    setNewMessage(newText);
    setShowEmojiPicker(false);
    inputRef.current?.focus();
  };

  const filteredMentions = teamMembers.filter(m => 
    m.full_name.toLowerCase().includes(mentionSearch) && m.id !== user?.id
  );

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim() && !attachmentPreview) return;

    try {
      const token = localStorage.getItem('token');
      const metadata = {};
      
      // Extract mentions
      const mentionRegex = /@([A-Za-z\s]+)/g;
      const mentions = [];
      let match;
      while ((match = mentionRegex.exec(newMessage)) !== null) {
        const mentionedMember = teamMembers.find(m => 
          m.full_name.toLowerCase() === match[1].trim().toLowerCase()
        );
        if (mentionedMember) {
          mentions.push(mentionedMember.id);
        }
      }
      if (mentions.length > 0) {
        metadata.mentions = mentions;
      }

      // Handle reply
      if (replyingTo) {
        metadata.reply_to = replyingTo.id;
        metadata.reply_preview = replyingTo.content.slice(0, 50);
      }

      // Handle attachment
      if (attachmentPreview) {
        metadata.attachment = attachmentPreview;
      }

      await axios.post(`${API_URL}/api/chat/messages`, {
        channel_id: selectedChannel.id,
        content: newMessage || (attachmentPreview ? `Shared: ${attachmentPreview.name}` : ''),
        type: attachmentPreview ? 'file' : 'text',
        metadata
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      setNewMessage('');
      setReplyingTo(null);
      setAttachmentPreview(null);
      fetchMessages();
    } catch (error) {
      toast.error('Failed to send message');
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      setAttachmentPreview({
        name: file.name,
        type: file.type,
        size: file.size,
        isImage: file.type.startsWith('image/')
      });
    }
  };

  const handleScheduleMeeting = async () => {
    if (!meetingForm.title || !meetingForm.scheduled_at) {
      toast.error('Please fill in meeting details');
      return;
    }

    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(`${API_URL}/api/appointments`, {
        title: meetingForm.title,
        lead_id: 'team-meeting',
        employee_id: user.id,
        scheduled_at: new Date(meetingForm.scheduled_at).toISOString(),
        duration: meetingForm.duration,
        meeting_link: meetingForm.meeting_link || `https://meet.leadgenpro.com/${Date.now()}`,
        notes: `Team meeting with: ${meetingForm.attendees.map(a => a.full_name).join(', ')}`
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });

      await axios.post(`${API_URL}/api/chat/messages`, {
        channel_id: selectedChannel.id,
        content: `📅 **Meeting Scheduled**\n${meetingForm.title}\n🕐 ${format(new Date(meetingForm.scheduled_at), 'PPp')}\n👥 ${meetingForm.attendees.length} attendees\n🔗 ${meetingForm.meeting_link || 'Link will be generated'}`,
        type: 'meeting',
        metadata: response.data
      }, {
        headers: { Authorization: `Bearer ${token}` }
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

  const handleViewAvailability = (member) => {
    setSelectedMember(member);
    fetchMemberAvailability(member.id);
    setShowAvailability(true);
  };

  const handleBookSlot = async (slot) => {
    setMeetingForm({
      ...meetingForm,
      scheduled_at: slot,
      attendees: [selectedMember]
    });
    setShowAvailability(false);
    setShowScheduler(true);
  };

  const copyBookingLink = (memberId) => {
    const link = `${window.location.origin}/book/${memberId}`;
    navigator.clipboard.writeText(link);
    toast.success('Booking link copied! Share it with anyone.');
  };

  const addReaction = async (messageId, emoji) => {
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API_URL}/api/chat/messages/${messageId}/reactions`, 
        { emoji },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      fetchMessages();
      setShowReactions(null);
    } catch (error) {
      toast.error('Failed to add reaction');
    }
  };

  // Get user status indicator
  const getUserStatusIndicator = (userId) => {
    const status = userStatuses[userId];
    if (!status) {
      return { color: 'bg-gray-400', emoji: '⚫', text: 'Offline' };
    }
    
    const preset = STATUS_PRESETS[status.status] || STATUS_PRESETS.offline;
    return {
      color: preset.color,
      emoji: status.status_emoji || preset.emoji,
      text: status.status_text || preset.text
    };
  };

  // Render message content with @mentions highlighted
  const renderMessageContent = (content, metadata) => {
    if (!content) return null;
    
    // Highlight @mentions
    const parts = content.split(/(@[A-Za-z\s]+)/g);
    return parts.map((part, i) => {
      if (part.startsWith('@')) {
        const name = part.slice(1).trim();
        const isMentioned = teamMembers.some(m => 
          m.full_name.toLowerCase() === name.toLowerCase()
        );
        if (isMentioned) {
          return (
            <span key={i} className="bg-blue-100 text-blue-800 px-1 rounded font-medium cursor-pointer hover:bg-blue-200">
              {part}
            </span>
          );
        }
      }
      return <span key={i}>{part}</span>;
    });
  };

  return (
    <>
      {/* Floating Chat Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-24 right-6 w-14 h-14 bg-gradient-to-br from-blue-600 to-blue-800 text-white rounded-full shadow-2xl hover:scale-110 transition-transform duration-200 flex items-center justify-center z-40"
          data-testid="team-chat-btn"
        >
          <MessageSquare className="w-6 h-6" />
          {Object.values(unreadCounts).some(c => c > 0) && (
            <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs font-bold rounded-full flex items-center justify-center">
              !
            </span>
          )}
        </button>
      )}

      {/* Chat Panel */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, x: 20, scale: 0.95 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 20, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className="fixed bottom-24 right-6 w-[900px] max-w-[calc(100vw-3rem)] h-[700px] max-h-[calc(100vh-10rem)] bg-white rounded-xl shadow-2xl border border-border overflow-hidden z-50 flex"
            data-testid="team-chat-panel"
          >
            {/* Sidebar */}
            <div className="w-72 bg-slate-900 flex flex-col">
              {/* Header with My Status */}
              <div className="p-4 border-b border-slate-800">
                <h3 className="text-white font-bold text-lg mb-3 flex items-center gap-2">
                  <MessageSquare className="w-5 h-5" />
                  Team Chat
                </h3>
                
                {/* My Status Selector */}
                <div className="relative">
                  <button
                    onClick={() => setShowStatusPicker(!showStatusPicker)}
                    className="w-full flex items-center gap-2 px-3 py-2 bg-slate-800 rounded-lg hover:bg-slate-700 transition-colors"
                  >
                    <span className="text-lg">{myStatus.status_emoji || '🟢'}</span>
                    <span className="text-sm text-slate-300 flex-1 text-left truncate">
                      {myStatus.status_text || 'Online'}
                    </span>
                    <ChevronDown className="w-4 h-4 text-slate-400" />
                  </button>
                  
                  {/* Status Picker Dropdown */}
                  <AnimatePresence>
                    {showStatusPicker && (
                      <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="absolute top-full left-0 right-0 mt-2 bg-slate-800 rounded-lg shadow-xl border border-slate-700 z-50 overflow-hidden"
                      >
                        <div className="p-2 max-h-64 overflow-y-auto">
                          <p className="text-xs text-slate-500 uppercase font-semibold px-2 py-1">Set Status</p>
                          {Object.entries(STATUS_PRESETS).map(([key, preset]) => (
                            <button
                              key={key}
                              onClick={() => updateMyStatus(key)}
                              className="w-full flex items-center gap-3 px-3 py-2 hover:bg-slate-700 rounded-lg transition-colors"
                            >
                              <span className="text-lg">{preset.emoji}</span>
                              <span className="text-sm text-slate-300">{preset.text}</span>
                            </button>
                          ))}
                        </div>
                        
                        {/* Duration options */}
                        <div className="border-t border-slate-700 p-2">
                          <p className="text-xs text-slate-500 uppercase font-semibold px-2 py-1">Clear After</p>
                          <div className="flex flex-wrap gap-1 px-2">
                            {[30, 60, 120, 240].map(mins => (
                              <button
                                key={mins}
                                onClick={() => updateMyStatus(myStatus.status, myStatus.status_text, mins)}
                                className="px-2 py-1 text-xs bg-slate-700 hover:bg-slate-600 rounded text-slate-300"
                              >
                                {mins < 60 ? `${mins}m` : `${mins/60}h`}
                              </button>
                            ))}
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>

                {/* View Toggle */}
                <div className="flex gap-2 mt-3">
                  <button
                    onClick={() => setActiveView('channels')}
                    className={`flex-1 px-3 py-2 rounded text-sm font-medium transition-colors ${
                      activeView === 'channels' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white hover:bg-slate-800'
                    }`}
                  >
                    <Hash className="w-4 h-4 inline mr-1" />
                    Channels
                  </button>
                  <button
                    onClick={() => setActiveView('direct')}
                    className={`flex-1 px-3 py-2 rounded text-sm font-medium transition-colors ${
                      activeView === 'direct' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white hover:bg-slate-800'
                    }`}
                  >
                    <User className="w-4 h-4 inline mr-1" />
                    Team
                  </button>
                </div>
              </div>

              {/* Channel/Team List */}
              <div className="flex-1 overflow-y-auto p-2">
                {activeView === 'channels' && (
                  <div className="space-y-1">
                    <div className="px-3 py-2 text-xs text-slate-500 uppercase font-semibold flex items-center justify-between">
                      Channels
                      <button className="text-slate-400 hover:text-white">
                        <Plus className="w-4 h-4" />
                      </button>
                    </div>
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
                        {unreadCounts[channel.id] > 0 && (
                          <span className="ml-auto bg-red-500 text-white text-xs px-1.5 rounded-full">
                            {unreadCounts[channel.id]}
                          </span>
                        )}
                      </button>
                    ))}
                  </div>
                )}

                {activeView === 'direct' && (
                  <div className="space-y-1">
                    <div className="px-3 py-2 text-xs text-slate-500 uppercase font-semibold">
                      Team Members
                    </div>
                    {teamMembers.filter(m => m.id !== user?.id).map((member) => {
                      const statusInfo = getUserStatusIndicator(member.id);
                      return (
                        <div key={member.id} className="group">
                          <button
                            className="w-full flex items-center gap-2 px-3 py-2 rounded text-left text-slate-300 hover:bg-slate-800 transition-colors"
                          >
                            <div className="relative">
                              <div className="w-8 h-8 bg-gradient-to-br from-primary to-accent rounded-full flex items-center justify-center text-white text-xs font-semibold">
                                {member.full_name.charAt(0)}
                              </div>
                              {/* Status indicator */}
                              <span 
                                className={`absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 ${statusInfo.color} border-2 border-slate-900 rounded-full flex items-center justify-center text-[8px]`}
                                title={statusInfo.text}
                              >
                                {statusInfo.emoji !== '🟢' && statusInfo.emoji !== '🟡' && statusInfo.emoji !== '🔴' && statusInfo.emoji !== '⚫' && statusInfo.emoji}
                              </span>
                            </div>
                            <div className="flex-1 min-w-0">
                              <span className="text-sm block truncate">{member.full_name}</span>
                              <span className="text-xs text-slate-500 flex items-center gap-1">
                                <span>{statusInfo.emoji}</span>
                                <span className="truncate">{statusInfo.text}</span>
                              </span>
                            </div>
                          </button>
                          {/* Quick actions on hover */}
                          <div className="hidden group-hover:flex items-center gap-1 px-3 pb-2">
                            <button
                              onClick={() => {
                                // Start DM by setting channel to user
                                setNewMessage(`@${member.full_name} `);
                                inputRef.current?.focus();
                              }}
                              className="p-1.5 bg-slate-800 hover:bg-slate-700 rounded text-slate-400 hover:text-white transition-colors"
                              title="Send message"
                            >
                              <MessageSquare className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => handleViewAvailability(member)}
                              className="p-1.5 bg-slate-800 hover:bg-slate-700 rounded text-slate-400 hover:text-white transition-colors"
                              title="View availability"
                            >
                              <CalendarDays className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => copyBookingLink(member.id)}
                              className="p-1.5 bg-slate-800 hover:bg-slate-700 rounded text-slate-400 hover:text-white transition-colors"
                              title="Copy booking link"
                            >
                              <Link2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </div>
                      );
                    })}
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
                  <div>
                    <h4 className="font-bold text-foreground">{selectedChannel?.name || 'Select a channel'}</h4>
                    <p className="text-xs text-secondary">{selectedChannel?.description}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setShowSearch(!showSearch)}
                    className={`p-2 rounded-lg transition-colors ${showSearch ? 'bg-blue-100 text-blue-600' : 'hover:bg-slate-100 text-secondary'}`}
                    title="Search messages"
                  >
                    <Search className="w-5 h-5" />
                  </button>
                  <button
                    onClick={() => setShowScheduler(true)}
                    className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
                    title="Schedule Meeting"
                  >
                    <Calendar className="w-5 h-5 text-secondary" />
                  </button>
                  <button
                    onClick={() => setIsOpen(false)}
                    className="p-2 bg-red-100 hover:bg-red-200 rounded-lg transition-colors border-2 border-red-300"
                    data-testid="close-team-chat-btn"
                    title="Close chat"
                  >
                    <X className="w-5 h-5 text-red-600" />
                  </button>
                </div>
              </div>

              {/* Search Bar */}
              <AnimatePresence>
                {showSearch && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="border-b border-border overflow-hidden"
                  >
                    <div className="p-3">
                      <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-secondary" />
                        <input
                          type="text"
                          value={searchQuery}
                          onChange={(e) => setSearchQuery(e.target.value)}
                          placeholder="Search messages..."
                          className="w-full pl-10 pr-4 py-2 border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50">
                {messages
                  .filter(m => !searchQuery || m.content?.toLowerCase().includes(searchQuery.toLowerCase()))
                  .map((msg, index) => {
                    const isThread = msg.metadata?.reply_to;
                    const senderStatus = getUserStatusIndicator(msg.sender_id);
                    
                    return (
                      <div key={index} className="group">
                        {/* Reply indicator */}
                        {isThread && (
                          <div className="flex items-center gap-2 text-xs text-secondary mb-1 ml-11">
                            <Reply className="w-3 h-3" />
                            <span>Replying to: {msg.metadata.reply_preview}...</span>
                          </div>
                        )}
                        
                        <div className="flex gap-3 hover:bg-white/50 rounded-lg p-2 -mx-2 transition-colors">
                          {/* Avatar with status */}
                          <div className="relative flex-shrink-0">
                            <div className="w-9 h-9 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center text-white font-semibold text-sm">
                              {msg.sender_name?.charAt(0) || 'U'}
                            </div>
                            <span 
                              className={`absolute -bottom-0.5 -right-0.5 w-3 h-3 ${senderStatus.color} border-2 border-white rounded-full`}
                              title={senderStatus.text}
                            />
                          </div>
                          
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="font-semibold text-foreground text-sm">{msg.sender_name}</span>
                              <span className="text-xs text-secondary">
                                {format(new Date(msg.created_at), 'h:mm a')}
                              </span>
                            </div>
                            
                            {/* Message content */}
                            <div className="text-sm text-foreground">
                              {msg.type === 'meeting' ? (
                                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                                  <div className="flex items-center gap-2 mb-2">
                                    <Calendar className="w-4 h-4 text-blue-600" />
                                    <span className="font-medium text-blue-800">Meeting Scheduled</span>
                                  </div>
                                  <div className="text-blue-700 whitespace-pre-line">{msg.content}</div>
                                </div>
                              ) : (
                                <div>{renderMessageContent(msg.content, msg.metadata)}</div>
                              )}
                              
                              {/* Attachment preview */}
                              {msg.metadata?.attachment && (
                                <div className="mt-2 flex items-center gap-2 p-2 bg-slate-100 rounded-lg max-w-xs">
                                  <File className="w-4 h-4 text-secondary" />
                                  <span className="text-sm truncate">{msg.metadata.attachment.name}</span>
                                </div>
                              )}
                            </div>
                            
                            {/* Reactions */}
                            {msg.reactions && Object.keys(msg.reactions).length > 0 && (
                              <div className="flex flex-wrap gap-1 mt-2">
                                {Object.entries(msg.reactions).map(([emoji, users]) => (
                                  <button
                                    key={emoji}
                                    onClick={() => addReaction(msg.id, emoji)}
                                    className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border transition-colors ${
                                      users.includes(user?.id) 
                                        ? 'bg-blue-100 border-blue-300 text-blue-700' 
                                        : 'bg-slate-100 border-slate-200 hover:bg-slate-200'
                                    }`}
                                  >
                                    <span>{emoji}</span>
                                    <span>{users.length}</span>
                                  </button>
                                ))}
                              </div>
                            )}
                          </div>
                          
                          {/* Action buttons on hover */}
                          <div className="opacity-0 group-hover:opacity-100 flex items-start gap-1 transition-opacity">
                            <button
                              onClick={() => setShowReactions(msg.id)}
                              className="p-1.5 hover:bg-slate-200 rounded transition-colors"
                              title="Add reaction"
                            >
                              <Smile className="w-4 h-4 text-secondary" />
                            </button>
                            <button
                              onClick={() => setReplyingTo(msg)}
                              className="p-1.5 hover:bg-slate-200 rounded transition-colors"
                              title="Reply"
                            >
                              <Reply className="w-4 h-4 text-secondary" />
                            </button>
                          </div>
                          
                          {/* Reaction picker */}
                          {showReactions === msg.id && (
                            <div className="absolute mt-8 bg-white rounded-lg shadow-xl border border-border p-2 flex gap-1 z-10">
                              {REACTION_EMOJIS.map(emoji => (
                                <button
                                  key={emoji}
                                  onClick={() => addReaction(msg.id, emoji)}
                                  className="w-8 h-8 hover:bg-slate-100 rounded flex items-center justify-center text-lg transition-colors"
                                >
                                  {emoji}
                                </button>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                <div ref={messagesEndRef} />
              </div>

              {/* Reply Preview */}
              <AnimatePresence>
                {replyingTo && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="px-4 py-2 bg-blue-50 border-t border-blue-200 flex items-center justify-between"
                  >
                    <div className="flex items-center gap-2 text-sm">
                      <Reply className="w-4 h-4 text-blue-600" />
                      <span className="text-blue-600">Replying to</span>
                      <span className="font-medium text-blue-800">{replyingTo.sender_name}</span>
                      <span className="text-blue-600 truncate max-w-xs">{replyingTo.content}</span>
                    </div>
                    <button
                      onClick={() => setReplyingTo(null)}
                      className="p-1 hover:bg-blue-100 rounded"
                    >
                      <X className="w-4 h-4 text-blue-600" />
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Message Input */}
              <form onSubmit={handleSendMessage} className="p-4 border-t border-border bg-white">
                {/* Attachment preview */}
                {attachmentPreview && (
                  <div className="mb-2 flex items-center gap-2 p-2 bg-slate-100 rounded-lg">
                    <File className="w-4 h-4 text-secondary" />
                    <span className="text-sm flex-1 truncate">{attachmentPreview.name}</span>
                    <button
                      type="button"
                      onClick={() => setAttachmentPreview(null)}
                      className="p-1 hover:bg-slate-200 rounded"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                )}
                
                <div className="flex items-end gap-2">
                  <div className="flex-1 relative">
                    {/* Mention suggestions */}
                    <AnimatePresence>
                      {showMentions && filteredMentions.length > 0 && (
                        <motion.div
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0, y: 10 }}
                          className="absolute bottom-full left-0 mb-2 w-64 bg-white rounded-lg shadow-xl border border-border max-h-48 overflow-y-auto"
                        >
                          {filteredMentions.map(member => {
                            const status = getUserStatusIndicator(member.id);
                            return (
                              <button
                                key={member.id}
                                type="button"
                                onClick={() => insertMention(member)}
                                className="w-full flex items-center gap-3 px-3 py-2 hover:bg-slate-50 transition-colors"
                              >
                                <div className="relative">
                                  <div className="w-8 h-8 bg-gradient-to-br from-primary to-accent rounded-full flex items-center justify-center text-white text-xs font-semibold">
                                    {member.full_name.charAt(0)}
                                  </div>
                                  <span className={`absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 ${status.color} border-2 border-white rounded-full`} />
                                </div>
                                <div className="flex-1 text-left">
                                  <span className="font-medium text-sm">{member.full_name}</span>
                                  <span className="text-xs text-secondary ml-2">{status.text}</span>
                                </div>
                              </button>
                            );
                          })}
                        </motion.div>
                      )}
                    </AnimatePresence>

                    {/* Emoji picker */}
                    <AnimatePresence>
                      {showEmojiPicker && (
                        <motion.div
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0, y: 10 }}
                          className="absolute bottom-full left-0 mb-2 bg-white rounded-lg shadow-xl border border-border p-3"
                        >
                          <div className="flex flex-wrap gap-1 max-w-[200px]">
                            {QUICK_EMOJIS.map(emoji => (
                              <button
                                key={emoji}
                                type="button"
                                onClick={() => insertEmoji(emoji)}
                                className="w-8 h-8 hover:bg-slate-100 rounded flex items-center justify-center text-lg transition-colors"
                              >
                                {emoji}
                              </button>
                            ))}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>

                    <div className="flex items-center border border-border rounded-lg bg-white focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-500">
                      <button
                        type="button"
                        onClick={() => setShowEmojiPicker(!showEmojiPicker)}
                        className="p-2 hover:bg-slate-100 rounded-l-lg transition-colors"
                      >
                        <Smile className="w-5 h-5 text-secondary" />
                      </button>
                      <input
                        ref={inputRef}
                        type="text"
                        value={newMessage}
                        onChange={handleInputChange}
                        placeholder={`Message #${selectedChannel?.name || 'channel'}... (type @ to mention)`}
                        className="flex-1 py-2 px-2 text-sm focus:outline-none"
                      />
                      <input
                        type="file"
                        ref={fileInputRef}
                        onChange={handleFileSelect}
                        className="hidden"
                      />
                      <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        className="p-2 hover:bg-slate-100 transition-colors"
                      >
                        <Paperclip className="w-5 h-5 text-secondary" />
                      </button>
                      <button
                        type="button"
                        onClick={() => setShowScheduler(true)}
                        className="p-2 hover:bg-slate-100 rounded-r-lg transition-colors"
                      >
                        <CalendarDays className="w-5 h-5 text-secondary" />
                      </button>
                    </div>
                  </div>
                  
                  <button
                    type="submit"
                    disabled={!newMessage.trim() && !attachmentPreview}
                    className="p-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
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
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-[60]"
            onClick={() => setShowScheduler(false)}
          >
            <motion.div
              initial={{ scale: 0.95 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.95 }}
              onClick={e => e.stopPropagation()}
              className="bg-white rounded-xl shadow-2xl w-[500px] max-w-[90vw] max-h-[80vh] overflow-y-auto"
            >
              <div className="p-6 border-b border-border">
                <h3 className="text-xl font-bold">Schedule Meeting</h3>
                <p className="text-secondary text-sm mt-1">Create a meeting and invite team members</p>
              </div>
              
              <div className="p-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Meeting Title</label>
                  <input
                    type="text"
                    value={meetingForm.title}
                    onChange={e => setMeetingForm(prev => ({ ...prev, title: e.target.value }))}
                    placeholder="e.g., Weekly Sync"
                    className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-2">Date & Time</label>
                  <input
                    type="datetime-local"
                    value={meetingForm.scheduled_at}
                    onChange={e => setMeetingForm(prev => ({ ...prev, scheduled_at: e.target.value }))}
                    className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-2">Duration</label>
                  <select
                    value={meetingForm.duration}
                    onChange={e => setMeetingForm(prev => ({ ...prev, duration: parseInt(e.target.value) }))}
                    className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value={15}>15 minutes</option>
                    <option value={30}>30 minutes</option>
                    <option value={45}>45 minutes</option>
                    <option value={60}>1 hour</option>
                    <option value={90}>1.5 hours</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-2">Invite Team Members</label>
                  <div className="max-h-40 overflow-y-auto border border-border rounded-lg p-2 space-y-1">
                    {teamMembers.filter(m => m.id !== user?.id).map(member => {
                      const isSelected = meetingForm.attendees.some(a => a.id === member.id);
                      const status = getUserStatusIndicator(member.id);
                      return (
                        <button
                          key={member.id}
                          type="button"
                          onClick={() => toggleAttendee(member)}
                          className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
                            isSelected ? 'bg-blue-100' : 'hover:bg-slate-50'
                          }`}
                        >
                          <div className="relative">
                            <div className="w-8 h-8 bg-gradient-to-br from-primary to-accent rounded-full flex items-center justify-center text-white text-xs font-semibold">
                              {member.full_name.charAt(0)}
                            </div>
                            <span className={`absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 ${status.color} border-2 border-white rounded-full`} />
                          </div>
                          <span className="flex-1 text-left text-sm">{member.full_name}</span>
                          {isSelected && <Check className="w-4 h-4 text-blue-600" />}
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>
              
              <div className="p-6 border-t border-border flex justify-end gap-3">
                <button
                  onClick={() => setShowScheduler(false)}
                  className="px-4 py-2 border border-border rounded-lg hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleScheduleMeeting}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Schedule Meeting
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Availability Modal */}
      <AnimatePresence>
        {showAvailability && selectedMember && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-[60]"
            onClick={() => setShowAvailability(false)}
          >
            <motion.div
              initial={{ scale: 0.95 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.95 }}
              onClick={e => e.stopPropagation()}
              className="bg-white rounded-xl shadow-2xl w-[400px] max-w-[90vw] max-h-[80vh] overflow-y-auto"
            >
              <div className="p-6 border-b border-border">
                <h3 className="text-xl font-bold">{selectedMember.full_name}&apos;s Availability</h3>
                <p className="text-secondary text-sm mt-1">Select a time slot to book</p>
              </div>
              
              <div className="p-6">
                {memberAvailability.length === 0 ? (
                  <p className="text-center text-secondary py-8">No available slots found</p>
                ) : (
                  <div className="space-y-2">
                    {memberAvailability.slice(0, 10).map((slot, i) => (
                      <button
                        key={i}
                        onClick={() => handleBookSlot(slot)}
                        className="w-full flex items-center justify-between px-4 py-3 border border-border rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors"
                      >
                        <span className="text-sm font-medium">
                          {format(new Date(slot), 'EEEE, MMM d')}
                        </span>
                        <span className="text-sm text-blue-600">
                          {format(new Date(slot), 'h:mm a')}
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
              
              <div className="p-6 border-t border-border">
                <button
                  onClick={() => copyBookingLink(selectedMember.id)}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2 border border-border rounded-lg hover:bg-slate-50 transition-colors"
                >
                  <Link2 className="w-4 h-4" />
                  Copy Public Booking Link
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};

export default TeamChatEnhanced;
