import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  MessageSquare, X, Send, Hash, User, Users, Calendar, 
  Paperclip, Video, Phone, Search, Plus, MoreVertical,
  AtSign, Reply, Check, CheckCheck, Image, File, Link2,
  Clock, CalendarDays, ExternalLink, ChevronDown, ChevronRight,
  Smile, ThumbsUp, Heart, Star, Bookmark
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { toast } from 'react-toastify';
import { format, formatDistanceToNow } from 'date-fns';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const TeamChat = () => {
  const { user } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [activeView, setActiveView] = useState('channels');
  const [selectedChannel, setSelectedChannel] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [channels, setChannels] = useState([]);
  const [teamMembers, setTeamMembers] = useState([]);
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

  useEffect(() => {
    if (isOpen) {
      fetchChannels();
      fetchTeamMembers();
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

  const fetchMemberAvailability = async (memberId) => {
    try {
      const response = await axios.get(`${API_URL}/api/booking/${memberId}/slots?days=7`);
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

  const filteredMentions = teamMembers.filter(m => 
    m.full_name.toLowerCase().includes(mentionSearch) && m.id !== user?.id
  );

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim() && !attachmentPreview) return;

    try {
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
      // In a real app, you'd upload this to a server
      // For now, we'll just show a preview
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
      const response = await axios.post(`${API_URL}/api/appointments`, {
        title: meetingForm.title,
        lead_id: 'team-meeting',
        employee_id: user.id,
        scheduled_at: new Date(meetingForm.scheduled_at).toISOString(),
        duration: meetingForm.duration,
        meeting_link: meetingForm.meeting_link || `https://meet.leadgenpro.com/${Date.now()}`,
        notes: `Team meeting with: ${meetingForm.attendees.map(a => a.full_name).join(', ')}`
      });

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

  const handleViewAvailability = (member) => {
    setSelectedMember(member);
    fetchMemberAvailability(member.id);
    setShowAvailability(true);
  };

  const handleBookSlot = async (slot) => {
    // Pre-fill the meeting scheduler with this slot
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

  const toggleThread = (messageId) => {
    setExpandedThreads(prev => ({
      ...prev,
      [messageId]: !prev[messageId]
    }));
  };

  const addReaction = async (messageId, emoji) => {
    // In a real app, this would call an API
    toast.success(`Reacted with ${emoji}`);
    setShowReactions(null);
  };

  // Parse message content for mentions and format
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
            <span key={i} className="bg-blue-100 text-blue-800 px-1 rounded font-medium">
              {part}
            </span>
          );
        }
      }
      return <span key={i}>{part}</span>;
    });
  };

  const getReadStatus = (msg) => {
    // Simulated read status
    const isRead = Math.random() > 0.3;
    return isRead ? 'read' : 'delivered';
  };

  const reactions = ['👍', '❤️', '😄', '🎉', '🤔', '👀'];

  return (
    <>
      {/* Floating Chat Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-24 right-6 w-14 h-14 bg-gradient-to-br from-blue-600 to-blue-800 text-white rounded-full shadow-2xl hover:scale-110 transition-transform duration-200 flex items-center justify-center z-40"
        data-testid="team-chat-btn"
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
            className="fixed bottom-24 right-6 w-[850px] h-[650px] bg-white rounded-xl shadow-2xl border border-border overflow-hidden z-40 flex"
            data-testid="team-chat-panel"
          >
            {/* Sidebar */}
            <div className="w-72 bg-slate-900 flex flex-col">
              <div className="p-4 border-b border-slate-800">
                <h3 className="text-white font-bold text-lg mb-4 flex items-center gap-2">
                  <MessageSquare className="w-5 h-5" />
                  Team Chat
                </h3>
                <div className="flex gap-2">
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
                      </button>
                    ))}
                  </div>
                )}

                {activeView === 'direct' && (
                  <div className="space-y-1">
                    <div className="px-3 py-2 text-xs text-slate-500 uppercase font-semibold">
                      Team Members
                    </div>
                    {teamMembers.filter(m => m.id !== user?.id).map((member) => (
                      <div key={member.id} className="group">
                        <button
                          className="w-full flex items-center gap-2 px-3 py-2 rounded text-left text-slate-300 hover:bg-slate-800 transition-colors"
                        >
                          <div className="relative">
                            <div className="w-8 h-8 bg-gradient-to-br from-primary to-accent rounded-full flex items-center justify-center text-white text-xs font-semibold">
                              {member.full_name.charAt(0)}
                            </div>
                            <span className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-green-500 border-2 border-slate-900 rounded-full"></span>
                          </div>
                          <div className="flex-1 min-w-0">
                            <span className="text-sm block truncate">{member.full_name}</span>
                            <span className="text-xs text-slate-500 capitalize">{member.role}</span>
                          </div>
                        </button>
                        {/* Quick actions on hover */}
                        <div className="hidden group-hover:flex items-center gap-1 px-3 pb-2">
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
                  <div>
                    <h4 className="font-bold text-foreground">{selectedChannel?.name || 'Select a channel'}</h4>
                    <p className="text-xs text-secondary">{selectedChannel?.description}</p>
                  </div>
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
                    className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
                    title="Search messages"
                  >
                    <Search className="w-5 h-5 text-secondary" />
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
                {messages.map((msg, index) => {
                  const isThread = msg.metadata?.reply_to;
                  const replies = messages.filter(m => m.metadata?.reply_to === msg.id);
                  const readStatus = getReadStatus(msg);
                  
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
                        <div className="w-9 h-9 bg-gradient-to-br from-primary to-accent rounded-lg flex items-center justify-center text-white text-xs font-semibold flex-shrink-0">
                          {msg.sender_name?.charAt(0) || 'U'}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-semibold text-sm text-foreground">{msg.sender_name}</span>
                            <span className="text-xs text-secondary">
                              {format(new Date(msg.created_at), 'p')}
                            </span>
                            {msg.sender_id === user?.id && (
                              <span className="text-xs text-secondary">
                                {readStatus === 'read' ? (
                                  <CheckCheck className="w-3.5 h-3.5 text-blue-500 inline" />
                                ) : (
                                  <Check className="w-3.5 h-3.5 inline" />
                                )}
                              </span>
                            )}
                          </div>
                          
                          <div className="text-sm text-foreground whitespace-pre-wrap">
                            {renderMessageContent(msg.content, msg.metadata)}
                          </div>
                          
                          {/* Attachment preview */}
                          {msg.metadata?.attachment && (
                            <div className="mt-2 p-3 bg-white border border-border rounded-lg inline-flex items-center gap-2">
                              {msg.metadata.attachment.isImage ? (
                                <Image className="w-5 h-5 text-blue-500" />
                              ) : (
                                <File className="w-5 h-5 text-blue-500" />
                              )}
                              <span className="text-sm">{msg.metadata.attachment.name}</span>
                            </div>
                          )}
                          
                          {/* Meeting card */}
                          {msg.type === 'meeting' && (
                            <div className="mt-2 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                              <div className="flex items-center gap-2 mb-2">
                                <Calendar className="w-5 h-5 text-blue-600" />
                                <span className="font-semibold text-blue-900">Meeting Invite</span>
                              </div>
                              <p className="text-sm text-blue-800 whitespace-pre-wrap">{msg.content}</p>
                              <button className="mt-3 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors">
                                Join Meeting
                              </button>
                            </div>
                          )}
                          
                          {/* Reactions */}
                          {msg.metadata?.reactions && msg.metadata.reactions.length > 0 && (
                            <div className="flex gap-1 mt-2">
                              {msg.metadata.reactions.map((r, i) => (
                                <span key={i} className="px-2 py-0.5 bg-white border border-border rounded-full text-xs">
                                  {r.emoji} {r.count}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                        
                        {/* Message actions */}
                        <div className="hidden group-hover:flex items-start gap-1">
                          <button
                            onClick={() => setReplyingTo(msg)}
                            className="p-1.5 hover:bg-slate-200 rounded transition-colors"
                            title="Reply"
                          >
                            <Reply className="w-4 h-4 text-secondary" />
                          </button>
                          <div className="relative">
                            <button
                              onClick={() => setShowReactions(showReactions === msg.id ? null : msg.id)}
                              className="p-1.5 hover:bg-slate-200 rounded transition-colors"
                              title="React"
                            >
                              <Smile className="w-4 h-4 text-secondary" />
                            </button>
                            {showReactions === msg.id && (
                              <div className="absolute top-full right-0 mt-1 bg-white border border-border rounded-lg shadow-lg p-2 flex gap-1 z-10">
                                {reactions.map(emoji => (
                                  <button
                                    key={emoji}
                                    onClick={() => addReaction(msg.id, emoji)}
                                    className="p-1 hover:bg-slate-100 rounded transition-colors text-lg"
                                  >
                                    {emoji}
                                  </button>
                                ))}
                              </div>
                            )}
                          </div>
                          <button className="p-1.5 hover:bg-slate-200 rounded transition-colors" title="Bookmark">
                            <Bookmark className="w-4 h-4 text-secondary" />
                          </button>
                        </div>
                      </div>
                      
                      {/* Thread replies */}
                      {replies.length > 0 && (
                        <div className="ml-12 mt-1">
                          <button
                            onClick={() => toggleThread(msg.id)}
                            className="text-xs text-blue-600 hover:underline flex items-center gap-1"
                          >
                            {expandedThreads[msg.id] ? (
                              <ChevronDown className="w-3 h-3" />
                            ) : (
                              <ChevronRight className="w-3 h-3" />
                            )}
                            {replies.length} {replies.length === 1 ? 'reply' : 'replies'}
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })}
                <div ref={messagesEndRef} />
              </div>

              {/* Reply Preview */}
              {replyingTo && (
                <div className="px-4 py-2 bg-blue-50 border-t border-blue-200 flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm">
                    <Reply className="w-4 h-4 text-blue-600" />
                    <span className="text-blue-800">Replying to {replyingTo.sender_name}:</span>
                    <span className="text-blue-600 truncate max-w-xs">{replyingTo.content.slice(0, 40)}...</span>
                  </div>
                  <button onClick={() => setReplyingTo(null)} className="text-blue-600 hover:text-blue-800">
                    <X className="w-4 h-4" />
                  </button>
                </div>
              )}

              {/* Attachment Preview */}
              {attachmentPreview && (
                <div className="px-4 py-2 bg-slate-100 border-t border-border flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm">
                    {attachmentPreview.isImage ? <Image className="w-4 h-4" /> : <File className="w-4 h-4" />}
                    <span>{attachmentPreview.name}</span>
                  </div>
                  <button onClick={() => setAttachmentPreview(null)} className="text-secondary hover:text-foreground">
                    <X className="w-4 h-4" />
                  </button>
                </div>
              )}

              {/* @Mention Dropdown */}
              {showMentions && filteredMentions.length > 0 && (
                <div className="px-4 py-2 border-t border-border bg-white">
                  <p className="text-xs text-secondary mb-2">Mention someone</p>
                  <div className="flex flex-wrap gap-2">
                    {filteredMentions.slice(0, 5).map(member => (
                      <button
                        key={member.id}
                        onClick={() => insertMention(member)}
                        className="flex items-center gap-2 px-3 py-1.5 bg-slate-100 hover:bg-blue-100 rounded-lg transition-colors"
                      >
                        <div className="w-6 h-6 bg-gradient-to-br from-primary to-accent rounded-full flex items-center justify-center text-white text-xs">
                          {member.full_name.charAt(0)}
                        </div>
                        <span className="text-sm font-medium">{member.full_name}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Input */}
              <form onSubmit={handleSendMessage} className="p-4 border-t border-border bg-white">
                <div className="flex gap-2">
                  <div className="flex-1 relative">
                    <input
                      ref={inputRef}
                      type="text"
                      value={newMessage}
                      onChange={handleInputChange}
                      placeholder={`Message #${selectedChannel?.name || 'channel'}... (type @ to mention)`}
                      className="w-full px-4 py-2.5 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary pr-24"
                    />
                    <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => setShowMentions(!showMentions)}
                        className="p-1.5 hover:bg-slate-100 rounded transition-colors"
                        title="Mention"
                      >
                        <AtSign className="w-4 h-4 text-secondary" />
                      </button>
                      <input
                        ref={fileInputRef}
                        type="file"
                        onChange={handleFileSelect}
                        className="hidden"
                        accept="image/*,.pdf,.doc,.docx,.xls,.xlsx"
                      />
                      <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        className="p-1.5 hover:bg-slate-100 rounded transition-colors"
                        title="Attach file"
                      >
                        <Paperclip className="w-4 h-4 text-secondary" />
                      </button>
                    </div>
                  </div>
                  <button
                    type="submit"
                    className="px-4 py-2 bg-primary text-white rounded-lg font-medium hover:bg-primary/90 transition-colors flex items-center gap-2"
                    data-testid="chat-send-btn"
                  >
                    <Send className="w-4 h-4" />
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
              <h3 className="text-2xl font-bold text-foreground mb-6 flex items-center gap-2">
                <Calendar className="w-6 h-6 text-primary" />
                Schedule Team Meeting
              </h3>

              <div className="space-y-4 mb-6">
                <div>
                  <label className="block text-sm font-medium mb-2">Meeting Title</label>
                  <input
                    type="text"
                    value={meetingForm.title}
                    onChange={(e) => setMeetingForm({...meetingForm, title: e.target.value})}
                    placeholder="e.g., Daily Standup, Sprint Planning"
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
                    <label className="block text-sm font-medium mb-2">Duration</label>
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
                  <label className="block text-sm font-medium mb-3">
                    Invite Team Members ({meetingForm.attendees.length} selected)
                  </label>
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

      {/* Availability Modal */}
      <AnimatePresence>
        {showAvailability && selectedMember && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-white rounded-xl p-6 max-w-md w-full max-h-[80vh] overflow-y-auto"
            >
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-gradient-to-br from-primary to-accent rounded-full flex items-center justify-center text-white font-bold">
                    {selectedMember.full_name.charAt(0)}
                  </div>
                  <div>
                    <h3 className="font-bold text-lg">{selectedMember.full_name}</h3>
                    <p className="text-sm text-secondary">Available times</p>
                  </div>
                </div>
                <button onClick={() => setShowAvailability(false)}>
                  <X className="w-5 h-5 text-secondary" />
                </button>
              </div>

              {/* Quick booking link */}
              <div className="p-3 bg-blue-50 rounded-lg mb-4 flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm text-blue-800">
                  <Link2 className="w-4 h-4" />
                  <span>Share booking link</span>
                </div>
                <button
                  onClick={() => copyBookingLink(selectedMember.id)}
                  className="px-3 py-1 bg-blue-600 text-white rounded text-sm font-medium hover:bg-blue-700"
                >
                  Copy Link
                </button>
              </div>

              {/* Available slots */}
              <div className="space-y-3">
                {memberAvailability.length > 0 ? (
                  memberAvailability.slice(0, 10).map((slot, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleBookSlot(slot)}
                      className="w-full flex items-center justify-between p-3 border border-border rounded-lg hover:border-primary hover:bg-primary/5 transition-all"
                    >
                      <div className="flex items-center gap-3">
                        <Clock className="w-5 h-5 text-primary" />
                        <div className="text-left">
                          <p className="font-medium">{format(new Date(slot), 'EEEE, MMM d')}</p>
                          <p className="text-sm text-secondary">{format(new Date(slot), 'h:mm a')}</p>
                        </div>
                      </div>
                      <ChevronRight className="w-5 h-5 text-secondary" />
                    </button>
                  ))
                ) : (
                  <div className="text-center py-8 text-secondary">
                    <CalendarDays className="w-12 h-12 mx-auto mb-2 opacity-50" />
                    <p>No available slots found</p>
                    <p className="text-sm mt-1">Try the booking page for more options</p>
                  </div>
                )}
              </div>

              <button
                onClick={() => window.open(`/book/${selectedMember.id}`, '_blank')}
                className="w-full mt-4 py-3 border-2 border-primary text-primary rounded-lg font-semibold hover:bg-primary/5 transition-colors flex items-center justify-center gap-2"
              >
                <ExternalLink className="w-4 h-4" />
                Open Full Booking Page
              </button>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </>
  );
};

export default TeamChat;
