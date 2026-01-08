import React, { useState, useEffect } from 'react';
import axios from 'axios';
import DashboardLayout from '@/components/DashboardLayout';
import { useAuth } from '@/context/AuthContext';
import { 
  Calendar, Clock, Plus, Edit2, Trash2, Copy, ExternalLink,
  Video, Phone, MapPin, Globe, Save, X, Palette, Settings,
  CheckCircle, AlertCircle, Link as LinkIcon, Users, Timer
} from 'lucide-react';
import { toast } from 'react-toastify';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Color options for meeting types
const COLOR_OPTIONS = [
  { name: 'Blue', value: '#3B82F6' },
  { name: 'Green', value: '#10B981' },
  { name: 'Purple', value: '#8B5CF6' },
  { name: 'Orange', value: '#F59E0B' },
  { name: 'Pink', value: '#EC4899' },
  { name: 'Red', value: '#EF4444' },
  { name: 'Teal', value: '#14B8A6' },
  { name: 'Indigo', value: '#6366F1' },
];

// Duration options
const DURATION_OPTIONS = [15, 30, 45, 60, 90, 120];

// Location options
const LOCATION_OPTIONS = [
  { value: 'google_meet', label: 'Google Meet', icon: Video },
  { value: 'zoom', label: 'Zoom', icon: Video },
  { value: 'phone', label: 'Phone Call', icon: Phone },
  { value: 'in_person', label: 'In Person', icon: MapPin },
];

// Standard meeting type templates
const MEETING_TEMPLATES = [
  { name: 'Quick Call', duration: 15, color: '#10B981', location: 'phone', description: 'A brief 15-minute call to answer questions' },
  { name: 'Discovery Call', duration: 30, color: '#3B82F6', location: 'google_meet', description: 'Learn about your needs and how we can help' },
  { name: 'Product Demo', duration: 45, color: '#8B5CF6', location: 'google_meet', description: 'Full product walkthrough and demonstration' },
  { name: 'Strategy Session', duration: 60, color: '#F59E0B', location: 'google_meet', description: 'In-depth discussion about your strategy' },
  { name: 'Consultation', duration: 60, color: '#EC4899', location: 'google_meet', description: 'Comprehensive consultation meeting' },
  { name: 'Technical Review', duration: 45, color: '#14B8A6', location: 'google_meet', description: 'Technical deep-dive and review session' },
];

const SchedulingSettingsPage = () => {
  const { user } = useAuth();
  const [meetingTypes, setMeetingTypes] = useState([]);
  const [availability, setAvailability] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingType, setEditingType] = useState(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showAvailabilityModal, setShowAvailabilityModal] = useState(false);
  const [activeTab, setActiveTab] = useState('types'); // 'types' or 'availability'
  
  // Form state for creating/editing meeting types
  const [formData, setFormData] = useState({
    name: '',
    duration: 30,
    description: '',
    color: '#3B82F6',
    location: 'google_meet',
    buffer_before: 0,
    buffer_after: 0,
    max_bookings_per_day: null,
    questions: []
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const token = localStorage.getItem('token');
      const [typesRes, availRes] = await Promise.all([
        axios.get(`${API_URL}/api/meeting-types`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get(`${API_URL}/api/availability`, {
          headers: { Authorization: `Bearer ${token}` }
        })
      ]);
      setMeetingTypes(typesRes.data);
      setAvailability(availRes.data);
    } catch (error) {
      console.error('Failed to fetch data:', error);
      toast.error('Failed to load scheduling settings');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateType = async () => {
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API_URL}/api/meeting-types`, formData, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Meeting type created successfully');
      setShowCreateModal(false);
      resetForm();
      fetchData();
    } catch (error) {
      toast.error('Failed to create meeting type');
    }
  };

  const handleUpdateType = async () => {
    try {
      const token = localStorage.getItem('token');
      await axios.put(`${API_URL}/api/meeting-types/${editingType.id}`, formData, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Meeting type updated successfully');
      setEditingType(null);
      resetForm();
      fetchData();
    } catch (error) {
      toast.error('Failed to update meeting type');
    }
  };

  const handleDeleteType = async (typeId) => {
    if (!window.confirm('Are you sure you want to delete this meeting type?')) return;
    
    try {
      const token = localStorage.getItem('token');
      await axios.delete(`${API_URL}/api/meeting-types/${typeId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Meeting type deleted');
      fetchData();
    } catch (error) {
      toast.error('Failed to delete meeting type');
    }
  };

  const handleSaveAvailability = async () => {
    try {
      const token = localStorage.getItem('token');
      await axios.put(`${API_URL}/api/availability`, availability, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Availability updated successfully');
      setShowAvailabilityModal(false);
    } catch (error) {
      toast.error('Failed to update availability');
    }
  };

  const handleUseTemplate = (template) => {
    setFormData({
      ...formData,
      name: template.name,
      duration: template.duration,
      description: template.description,
      color: template.color,
      location: template.location,
    });
  };

  const resetForm = () => {
    setFormData({
      name: '',
      duration: 30,
      description: '',
      color: '#3B82F6',
      location: 'google_meet',
      buffer_before: 0,
      buffer_after: 0,
      max_bookings_per_day: null,
      questions: []
    });
  };

  const copyBookingLink = () => {
    const baseUrl = window.location.origin;
    const link = `${baseUrl}/book/${user?.id}`;
    navigator.clipboard.writeText(link);
    toast.success('Booking link copied to clipboard!');
  };

  const openBookingPage = () => {
    const baseUrl = window.location.origin;
    window.open(`${baseUrl}/book/${user?.id}`, '_blank');
  };

  const getLocationIcon = (location) => {
    const option = LOCATION_OPTIONS.find(o => o.value === location);
    return option ? option.icon : Globe;
  };

  const dayNames = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="p-4 md:p-6 max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
                <Calendar className="w-7 h-7 text-primary" />
                Scheduling Settings
              </h1>
              <p className="text-secondary mt-1">
                Manage your meeting types and availability like Calendly
              </p>
            </div>
            
            <div className="flex items-center gap-2">
              <button
                onClick={copyBookingLink}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 rounded-lg flex items-center gap-2 transition-colors"
              >
                <Copy className="w-4 h-4" />
                <span className="hidden sm:inline">Copy Link</span>
              </button>
              <button
                onClick={openBookingPage}
                className="px-4 py-2 bg-primary text-white rounded-lg flex items-center gap-2 hover:bg-primary/90 transition-colors"
              >
                <ExternalLink className="w-4 h-4" />
                <span className="hidden sm:inline">Preview</span>
              </button>
            </div>
          </div>
        </div>

        {/* Booking Link Card */}
        <div className="bg-gradient-to-r from-primary/10 to-accent/10 border border-primary/20 rounded-xl p-4 mb-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-primary/20 rounded-lg flex items-center justify-center">
                <LinkIcon className="w-5 h-5 text-primary" />
              </div>
              <div>
                <p className="text-sm text-secondary">Your Booking Link</p>
                <p className="font-medium text-foreground break-all">
                  {window.location.origin}/book/{user?.id}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded-full flex items-center gap-1">
                <CheckCircle className="w-3 h-3" />
                Active
              </span>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-border mb-6">
          <button
            onClick={() => setActiveTab('types')}
            className={`px-4 py-3 font-medium border-b-2 transition-colors ${
              activeTab === 'types'
                ? 'border-primary text-primary'
                : 'border-transparent text-secondary hover:text-foreground'
            }`}
          >
            <Clock className="w-4 h-4 inline mr-2" />
            Meeting Types
          </button>
          <button
            onClick={() => setActiveTab('availability')}
            className={`px-4 py-3 font-medium border-b-2 transition-colors ${
              activeTab === 'availability'
                ? 'border-primary text-primary'
                : 'border-transparent text-secondary hover:text-foreground'
            }`}
          >
            <Calendar className="w-4 h-4 inline mr-2" />
            Availability
          </button>
        </div>

        {/* Meeting Types Tab */}
        {activeTab === 'types' && (
          <div>
            {/* Add Meeting Type Button */}
            <div className="mb-6">
              <button
                onClick={() => setShowCreateModal(true)}
                className="px-4 py-2 bg-primary text-white rounded-lg flex items-center gap-2 hover:bg-primary/90 transition-colors"
              >
                <Plus className="w-5 h-5" />
                New Meeting Type
              </button>
            </div>

            {/* Meeting Types Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {meetingTypes.map((type) => {
                const LocationIcon = getLocationIcon(type.location);
                return (
                  <div
                    key={type.id}
                    className="bg-white border border-border rounded-xl overflow-hidden hover:shadow-md transition-shadow"
                  >
                    <div className="h-2" style={{ backgroundColor: type.color }} />
                    <div className="p-4">
                      <div className="flex items-start justify-between mb-3">
                        <h3 className="font-semibold text-foreground">{type.name}</h3>
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => {
                              setEditingType(type);
                              setFormData({
                                name: type.name,
                                duration: type.duration,
                                description: type.description || '',
                                color: type.color,
                                location: type.location,
                                buffer_before: type.buffer_before || 0,
                                buffer_after: type.buffer_after || 0,
                                max_bookings_per_day: type.max_bookings_per_day,
                                questions: type.questions || []
                              });
                            }}
                            className="p-1.5 hover:bg-slate-100 rounded-lg transition-colors"
                          >
                            <Edit2 className="w-4 h-4 text-secondary" />
                          </button>
                          <button
                            onClick={() => handleDeleteType(type.id)}
                            className="p-1.5 hover:bg-red-50 rounded-lg transition-colors"
                          >
                            <Trash2 className="w-4 h-4 text-red-500" />
                          </button>
                        </div>
                      </div>
                      
                      {type.description && (
                        <p className="text-sm text-secondary mb-3 line-clamp-2">
                          {type.description}
                        </p>
                      )}
                      
                      <div className="flex items-center gap-4 text-sm text-secondary">
                        <span className="flex items-center gap-1">
                          <Clock className="w-4 h-4" />
                          {type.duration} min
                        </span>
                        <span className="flex items-center gap-1">
                          <LocationIcon className="w-4 h-4" />
                          {LOCATION_OPTIONS.find(o => o.value === type.location)?.label || type.location}
                        </span>
                      </div>
                      
                      <div className="mt-4 pt-3 border-t border-border">
                        <button
                          onClick={() => {
                            const link = `${window.location.origin}/book/${user?.id}?type=${type.id}`;
                            navigator.clipboard.writeText(link);
                            toast.success('Link copied!');
                          }}
                          className="w-full py-2 text-sm text-primary hover:bg-primary/5 rounded-lg transition-colors flex items-center justify-center gap-2"
                        >
                          <Copy className="w-4 h-4" />
                          Copy Direct Link
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {meetingTypes.length === 0 && (
              <div className="text-center py-12 bg-slate-50 rounded-xl">
                <Calendar className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-foreground mb-2">No meeting types yet</h3>
                <p className="text-secondary mb-4">Create your first meeting type to start accepting bookings</p>
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="px-4 py-2 bg-primary text-white rounded-lg"
                >
                  Create Meeting Type
                </button>
              </div>
            )}
          </div>
        )}

        {/* Availability Tab */}
        {activeTab === 'availability' && (
          <div className="bg-white border border-border rounded-xl p-6">
            <h3 className="font-semibold text-foreground mb-4 flex items-center gap-2">
              <Timer className="w-5 h-5 text-primary" />
              Weekly Availability
            </h3>
            <p className="text-secondary text-sm mb-6">
              Set your available hours for each day of the week
            </p>
            
            <div className="space-y-4">
              {dayNames.map((day, index) => {
                const rule = availability.find(r => r.day_of_week === index) || {
                  day_of_week: index,
                  start_time: '09:00',
                  end_time: '17:00',
                  is_available: false
                };
                
                return (
                  <div key={index} className="flex flex-col sm:flex-row sm:items-center gap-3 py-3 border-b border-border last:border-0">
                    <div className="w-28 flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={rule.is_available}
                        onChange={(e) => {
                          const newAvailability = [...availability];
                          const existing = newAvailability.find(r => r.day_of_week === index);
                          if (existing) {
                            existing.is_available = e.target.checked;
                          } else {
                            newAvailability.push({
                              day_of_week: index,
                              start_time: '09:00',
                              end_time: '17:00',
                              is_available: e.target.checked
                            });
                          }
                          setAvailability(newAvailability);
                        }}
                        className="w-4 h-4 text-primary rounded"
                      />
                      <span className={rule.is_available ? 'text-foreground font-medium' : 'text-secondary'}>
                        {day}
                      </span>
                    </div>
                    
                    {rule.is_available && (
                      <div className="flex items-center gap-2 ml-6 sm:ml-0">
                        <input
                          type="time"
                          value={rule.start_time || '09:00'}
                          onChange={(e) => {
                            const newAvailability = [...availability];
                            const existing = newAvailability.find(r => r.day_of_week === index);
                            if (existing) {
                              existing.start_time = e.target.value;
                            }
                            setAvailability(newAvailability);
                          }}
                          className="px-3 py-1.5 border border-border rounded-lg text-sm"
                        />
                        <span className="text-secondary">to</span>
                        <input
                          type="time"
                          value={rule.end_time || '17:00'}
                          onChange={(e) => {
                            const newAvailability = [...availability];
                            const existing = newAvailability.find(r => r.day_of_week === index);
                            if (existing) {
                              existing.end_time = e.target.value;
                            }
                            setAvailability(newAvailability);
                          }}
                          className="px-3 py-1.5 border border-border rounded-lg text-sm"
                        />
                      </div>
                    )}
                    
                    {!rule.is_available && (
                      <span className="text-sm text-secondary ml-6 sm:ml-0">Unavailable</span>
                    )}
                  </div>
                );
              })}
            </div>
            
            <div className="mt-6 pt-4 border-t border-border">
              <button
                onClick={handleSaveAvailability}
                className="px-4 py-2 bg-primary text-white rounded-lg flex items-center gap-2 hover:bg-primary/90"
              >
                <Save className="w-4 h-4" />
                Save Availability
              </button>
            </div>
          </div>
        )}

        {/* Create/Edit Modal */}
        {(showCreateModal || editingType) && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
              <div className="p-6 border-b border-border flex items-center justify-between sticky top-0 bg-white">
                <h2 className="text-xl font-bold text-foreground">
                  {editingType ? 'Edit Meeting Type' : 'Create Meeting Type'}
                </h2>
                <button
                  onClick={() => {
                    setShowCreateModal(false);
                    setEditingType(null);
                    resetForm();
                  }}
                  className="p-2 hover:bg-slate-100 rounded-lg"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              
              <div className="p-6">
                {/* Quick Templates */}
                {!editingType && (
                  <div className="mb-6">
                    <label className="block text-sm font-medium mb-2">Quick Start Templates</label>
                    <div className="flex flex-wrap gap-2">
                      {MEETING_TEMPLATES.map((template) => (
                        <button
                          key={template.name}
                          onClick={() => handleUseTemplate(template)}
                          className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 rounded-lg text-sm transition-colors"
                        >
                          {template.name}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Form Fields */}
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Meeting Name <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      placeholder="e.g., Discovery Call"
                      className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium mb-2">Description</label>
                    <textarea
                      value={formData.description}
                      onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                      placeholder="Brief description of this meeting type"
                      rows={2}
                      className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium mb-2">
                        Duration <span className="text-red-500">*</span>
                      </label>
                      <select
                        value={formData.duration}
                        onChange={(e) => setFormData({ ...formData, duration: parseInt(e.target.value) })}
                        className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                      >
                        {DURATION_OPTIONS.map((d) => (
                          <option key={d} value={d}>{d} minutes</option>
                        ))}
                      </select>
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium mb-2">Location</label>
                      <select
                        value={formData.location}
                        onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                        className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                      >
                        {LOCATION_OPTIONS.map((loc) => (
                          <option key={loc.value} value={loc.value}>{loc.label}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium mb-2">Color</label>
                    <div className="flex flex-wrap gap-2">
                      {COLOR_OPTIONS.map((color) => (
                        <button
                          key={color.value}
                          onClick={() => setFormData({ ...formData, color: color.value })}
                          className={`w-8 h-8 rounded-full transition-transform ${
                            formData.color === color.value ? 'ring-2 ring-offset-2 ring-slate-400 scale-110' : ''
                          }`}
                          style={{ backgroundColor: color.value }}
                          title={color.name}
                        />
                      ))}
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium mb-2">Buffer Before (min)</label>
                      <input
                        type="number"
                        value={formData.buffer_before}
                        onChange={(e) => setFormData({ ...formData, buffer_before: parseInt(e.target.value) || 0 })}
                        min={0}
                        max={60}
                        className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                      />
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium mb-2">Buffer After (min)</label>
                      <input
                        type="number"
                        value={formData.buffer_after}
                        onChange={(e) => setFormData({ ...formData, buffer_after: parseInt(e.target.value) || 0 })}
                        min={0}
                        max={60}
                        className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                      />
                    </div>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium mb-2">Max Bookings Per Day (optional)</label>
                    <input
                      type="number"
                      value={formData.max_bookings_per_day || ''}
                      onChange={(e) => setFormData({ 
                        ...formData, 
                        max_bookings_per_day: e.target.value ? parseInt(e.target.value) : null 
                      })}
                      min={1}
                      placeholder="Unlimited"
                      className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                  </div>
                </div>
                
                {/* Preview */}
                <div className="mt-6 p-4 bg-slate-50 rounded-xl">
                  <h4 className="text-sm font-medium text-secondary mb-3">Preview</h4>
                  <div className="bg-white border border-border rounded-lg overflow-hidden">
                    <div className="h-2" style={{ backgroundColor: formData.color }} />
                    <div className="p-4">
                      <h3 className="font-semibold">{formData.name || 'Meeting Name'}</h3>
                      {formData.description && (
                        <p className="text-sm text-secondary mt-1">{formData.description}</p>
                      )}
                      <div className="flex items-center gap-4 mt-2 text-sm text-secondary">
                        <span className="flex items-center gap-1">
                          <Clock className="w-4 h-4" />
                          {formData.duration} min
                        </span>
                        <span className="flex items-center gap-1">
                          {React.createElement(getLocationIcon(formData.location), { className: "w-4 h-4" })}
                          {LOCATION_OPTIONS.find(o => o.value === formData.location)?.label}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              
              <div className="p-6 border-t border-border flex justify-end gap-3 sticky bottom-0 bg-white">
                <button
                  onClick={() => {
                    setShowCreateModal(false);
                    setEditingType(null);
                    resetForm();
                  }}
                  className="px-4 py-2 border border-border rounded-lg hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  onClick={editingType ? handleUpdateType : handleCreateType}
                  disabled={!formData.name}
                  className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2"
                >
                  <Save className="w-4 h-4" />
                  {editingType ? 'Update' : 'Create'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
};

export default SchedulingSettingsPage;
