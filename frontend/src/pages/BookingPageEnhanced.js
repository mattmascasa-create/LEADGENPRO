import React, { useState, useEffect } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { 
  Calendar, Clock, User, Building, Mail, Phone, 
  ChevronLeft, ChevronRight, Check, Video, MapPin,
  Globe, Sparkles, ArrowRight, ExternalLink
} from 'lucide-react';
import { toast } from 'react-toastify';
import { format, addDays, startOfWeek, isSameDay, parseISO } from 'date-fns';
import { motion, AnimatePresence } from 'framer-motion';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const BookingPageEnhanced = () => {
  const { userId } = useParams();
  const [searchParams] = useSearchParams();
  const preselectedType = searchParams.get('type');
  
  const [hostUser, setHostUser] = useState(null);
  const [meetingTypes, setMeetingTypes] = useState([]);
  const [selectedType, setSelectedType] = useState(null);
  const [loading, setLoading] = useState(true);
  const [step, setStep] = useState(1); // 1: Select Type, 2: Select Date/Time, 3: Enter Details, 4: Confirmed
  
  const [selectedDate, setSelectedDate] = useState(null);
  const [selectedTime, setSelectedTime] = useState(null);
  const [currentWeekStart, setCurrentWeekStart] = useState(startOfWeek(new Date(), { weekStartsOn: 1 }));
  const [availableSlots, setAvailableSlots] = useState([]);
  const [slotsByDate, setSlotsByDate] = useState({});
  
  const [bookingDetails, setBookingDetails] = useState({
    name: '',
    email: '',
    phone: '',
    company: '',
    notes: ''
  });
  const [answers, setAnswers] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [confirmedBooking, setConfirmedBooking] = useState(null);

  useEffect(() => {
    fetchHostAndMeetingTypes();
  }, [userId]);

  useEffect(() => {
    if (selectedType) {
      fetchAvailableSlots();
    }
  }, [selectedType, currentWeekStart]);

  const fetchHostAndMeetingTypes = async () => {
    try {
      // Fetch host user info
      const userResponse = await axios.get(`${API_URL}/api/booking/${userId}`);
      setHostUser(userResponse.data.user);
      
      // Fetch meeting types
      const typesResponse = await axios.get(`${API_URL}/api/booking/${userId}/meeting-types`);
      setMeetingTypes(typesResponse.data);
      
      // Auto-select if preselected type
      if (preselectedType && typesResponse.data.length > 0) {
        const type = typesResponse.data.find(t => t.id === preselectedType);
        if (type) {
          setSelectedType(type);
          setStep(2);
        }
      }
    } catch (error) {
      toast.error('Failed to load booking page');
    } finally {
      setLoading(false);
    }
  };

  const fetchAvailableSlots = async () => {
    if (!selectedType) return;
    
    try {
      const response = await axios.get(
        `${API_URL}/api/booking/${userId}/slots/${selectedType.id}`,
        { params: { days: 14 } }
      );
      
      const slots = response.data.available_slots || [];
      
      // Group slots by date
      const grouped = {};
      slots.forEach(slot => {
        const date = format(parseISO(slot), 'yyyy-MM-dd');
        if (!grouped[date]) {
          grouped[date] = [];
        }
        grouped[date].push(slot);
      });
      
      setSlotsByDate(grouped);
      setAvailableSlots(slots);
    } catch (error) {
      console.error('Failed to fetch slots:', error);
      toast.error('Failed to load available times');
    }
  };

  const handleSelectType = (type) => {
    setSelectedType(type);
    setStep(2);
  };

  const handleSelectDate = (date) => {
    setSelectedDate(date);
    setSelectedTime(null);
  };

  const handleSelectTime = (slot) => {
    setSelectedTime(slot);
    setStep(3);
  };

  const handleBooking = async (e) => {
    e.preventDefault();
    
    if (!bookingDetails.name || !bookingDetails.email) {
      toast.error('Please fill in required fields');
      return;
    }

    setIsSubmitting(true);
    
    try {
      const response = await axios.post(`${API_URL}/api/booking/${userId}/book`, {
        meeting_type_id: selectedType.id,
        scheduled_at: selectedTime,
        name: bookingDetails.name,
        email: bookingDetails.email,
        phone: bookingDetails.phone,
        company: bookingDetails.company,
        notes: bookingDetails.notes,
        answers
      });
      
      setConfirmedBooking(response.data);
      setStep(4);
      toast.success('Meeting booked successfully!');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to book meeting');
    } finally {
      setIsSubmitting(false);
    }
  };

  const getLocationIcon = (location) => {
    switch (location) {
      case 'google_meet':
        return <Video className="w-4 h-4" />;
      case 'zoom':
        return <Video className="w-4 h-4" />;
      case 'phone':
        return <Phone className="w-4 h-4" />;
      case 'in_person':
        return <MapPin className="w-4 h-4" />;
      default:
        return <Globe className="w-4 h-4" />;
    }
  };

  const getLocationText = (location) => {
    switch (location) {
      case 'google_meet':
        return 'Google Meet';
      case 'zoom':
        return 'Zoom';
      case 'phone':
        return 'Phone Call';
      case 'in_person':
        return 'In Person';
      default:
        return 'Online';
    }
  };

  // Generate week days for calendar
  const weekDays = [];
  for (let i = 0; i < 7; i++) {
    weekDays.push(addDays(currentWeekStart, i));
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-20 h-20 bg-gradient-to-br from-primary to-accent rounded-full flex items-center justify-center text-white text-2xl font-bold mx-auto mb-4 shadow-lg">
            {hostUser?.full_name?.charAt(0) || 'U'}
          </div>
          <h1 className="text-2xl font-bold text-foreground mb-1">{hostUser?.full_name}</h1>
          <p className="text-secondary">{hostUser?.company || 'LeadGen Pro'}</p>
        </div>

        {/* Progress Steps */}
        <div className="flex items-center justify-center gap-2 mb-8">
          {[1, 2, 3, 4].map((s) => (
            <React.Fragment key={s}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors ${
                step >= s 
                  ? 'bg-primary text-white' 
                  : 'bg-slate-200 text-slate-500'
              }`}>
                {step > s ? <Check className="w-4 h-4" /> : s}
              </div>
              {s < 4 && (
                <div className={`w-12 h-1 rounded ${step > s ? 'bg-primary' : 'bg-slate-200'}`} />
              )}
            </React.Fragment>
          ))}
        </div>

        <AnimatePresence mode="wait">
          {/* Step 1: Select Meeting Type */}
          {step === 1 && (
            <motion.div
              key="step1"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="bg-white rounded-2xl shadow-xl p-8"
            >
              <h2 className="text-xl font-bold text-foreground mb-2">Select a Meeting Type</h2>
              <p className="text-secondary mb-6">Choose the type of meeting you&apos;d like to schedule</p>
              
              <div className="grid gap-4">
                {meetingTypes.map((type) => (
                  <button
                    key={type.id}
                    onClick={() => handleSelectType(type)}
                    className="group p-6 border-2 border-slate-200 rounded-xl hover:border-primary hover:bg-primary/5 transition-all text-left"
                  >
                    <div className="flex items-start gap-4">
                      <div 
                        className="w-2 h-full rounded-full"
                        style={{ backgroundColor: type.color }}
                      />
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-2">
                          <h3 className="text-lg font-semibold text-foreground group-hover:text-primary transition-colors">
                            {type.name}
                          </h3>
                          <ArrowRight className="w-5 h-5 text-slate-400 group-hover:text-primary group-hover:translate-x-1 transition-all" />
                        </div>
                        {type.description && (
                          <p className="text-secondary text-sm mb-3">{type.description}</p>
                        )}
                        <div className="flex items-center gap-4 text-sm text-secondary">
                          <span className="flex items-center gap-1">
                            <Clock className="w-4 h-4" />
                            {type.duration} min
                          </span>
                          <span className="flex items-center gap-1">
                            {getLocationIcon(type.location)}
                            {getLocationText(type.location)}
                          </span>
                        </div>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </motion.div>
          )}

          {/* Step 2: Select Date & Time */}
          {step === 2 && selectedType && (
            <motion.div
              key="step2"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="bg-white rounded-2xl shadow-xl overflow-hidden"
            >
              {/* Selected type header */}
              <div className="bg-slate-50 p-4 border-b border-border flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div 
                    className="w-3 h-12 rounded-full"
                    style={{ backgroundColor: selectedType.color }}
                  />
                  <div>
                    <h3 className="font-semibold text-foreground">{selectedType.name}</h3>
                    <p className="text-sm text-secondary flex items-center gap-2">
                      <Clock className="w-4 h-4" />
                      {selectedType.duration} min
                      <span className="mx-1">•</span>
                      {getLocationIcon(selectedType.location)}
                      {getLocationText(selectedType.location)}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => { setStep(1); setSelectedType(null); }}
                  className="text-sm text-primary hover:underline"
                >
                  Change
                </button>
              </div>

              <div className="p-6">
                <h2 className="text-xl font-bold text-foreground mb-6">Select Date & Time</h2>
                
                <div className="flex flex-col lg:flex-row gap-6">
                  {/* Calendar */}
                  <div className="lg:w-1/2">
                    <div className="flex items-center justify-between mb-4">
                      <button
                        onClick={() => setCurrentWeekStart(addDays(currentWeekStart, -7))}
                        className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
                      >
                        <ChevronLeft className="w-5 h-5" />
                      </button>
                      <span className="font-medium">
                        {format(currentWeekStart, 'MMMM yyyy')}
                      </span>
                      <button
                        onClick={() => setCurrentWeekStart(addDays(currentWeekStart, 7))}
                        className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
                      >
                        <ChevronRight className="w-5 h-5" />
                      </button>
                    </div>
                    
                    <div className="grid grid-cols-7 gap-2">
                      {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map(day => (
                        <div key={day} className="text-center text-xs text-secondary font-medium py-2">
                          {day}
                        </div>
                      ))}
                      
                      {weekDays.map((date, i) => {
                        const dateKey = format(date, 'yyyy-MM-dd');
                        const hasSlots = slotsByDate[dateKey]?.length > 0;
                        const isSelected = selectedDate && isSameDay(date, selectedDate);
                        const isPast = date < new Date().setHours(0, 0, 0, 0);
                        
                        return (
                          <button
                            key={i}
                            onClick={() => hasSlots && !isPast && handleSelectDate(date)}
                            disabled={!hasSlots || isPast}
                            className={`p-3 rounded-lg text-center transition-all ${
                              isSelected
                                ? 'bg-primary text-white'
                                : hasSlots && !isPast
                                  ? 'hover:bg-primary/10 text-foreground'
                                  : 'text-slate-300 cursor-not-allowed'
                            }`}
                          >
                            <span className="text-lg font-medium">{format(date, 'd')}</span>
                            {hasSlots && !isPast && (
                              <div className={`w-1.5 h-1.5 rounded-full mx-auto mt-1 ${
                                isSelected ? 'bg-white' : 'bg-primary'
                              }`} />
                            )}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Time slots */}
                  <div className="lg:w-1/2">
                    {selectedDate ? (
                      <>
                        <h3 className="font-medium text-foreground mb-4">
                          {format(selectedDate, 'EEEE, MMMM d')}
                        </h3>
                        <div className="grid grid-cols-2 gap-2 max-h-80 overflow-y-auto">
                          {(slotsByDate[format(selectedDate, 'yyyy-MM-dd')] || []).map((slot, i) => (
                            <button
                              key={i}
                              onClick={() => handleSelectTime(slot)}
                              className={`px-4 py-3 rounded-lg text-sm font-medium transition-all ${
                                selectedTime === slot
                                  ? 'bg-primary text-white'
                                  : 'border border-border hover:border-primary hover:text-primary'
                              }`}
                            >
                              {format(parseISO(slot), 'h:mm a')}
                            </button>
                          ))}
                        </div>
                      </>
                    ) : (
                      <div className="flex items-center justify-center h-full text-secondary">
                        <Calendar className="w-6 h-6 mr-2" />
                        Select a date to see available times
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {/* Step 3: Enter Details */}
          {step === 3 && (
            <motion.div
              key="step3"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="bg-white rounded-2xl shadow-xl p-8"
            >
              {/* Booking summary */}
              <div className="bg-slate-50 rounded-xl p-4 mb-6">
                <div className="flex items-center gap-3 mb-3">
                  <div 
                    className="w-3 h-10 rounded-full"
                    style={{ backgroundColor: selectedType?.color }}
                  />
                  <div>
                    <h3 className="font-semibold text-foreground">{selectedType?.name}</h3>
                    <p className="text-sm text-secondary">with {hostUser?.full_name}</p>
                  </div>
                </div>
                <div className="flex items-center gap-4 text-sm">
                  <span className="flex items-center gap-1 text-foreground">
                    <Calendar className="w-4 h-4 text-secondary" />
                    {selectedTime && format(parseISO(selectedTime), 'EEEE, MMMM d, yyyy')}
                  </span>
                  <span className="flex items-center gap-1 text-foreground">
                    <Clock className="w-4 h-4 text-secondary" />
                    {selectedTime && format(parseISO(selectedTime), 'h:mm a')}
                  </span>
                </div>
              </div>

              <h2 className="text-xl font-bold text-foreground mb-6">Enter Your Details</h2>
              
              <form onSubmit={handleBooking} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Name <span className="text-red-500">*</span>
                    </label>
                    <div className="relative">
                      <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-secondary" />
                      <input
                        type="text"
                        value={bookingDetails.name}
                        onChange={e => setBookingDetails(prev => ({ ...prev, name: e.target.value }))}
                        placeholder="Your full name"
                        required
                        className="w-full pl-10 pr-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                      />
                    </div>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Email <span className="text-red-500">*</span>
                    </label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-secondary" />
                      <input
                        type="email"
                        value={bookingDetails.email}
                        onChange={e => setBookingDetails(prev => ({ ...prev, email: e.target.value }))}
                        placeholder="your@email.com"
                        required
                        className="w-full pl-10 pr-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                      />
                    </div>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium mb-2">Phone</label>
                    <div className="relative">
                      <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-secondary" />
                      <input
                        type="tel"
                        value={bookingDetails.phone}
                        onChange={e => setBookingDetails(prev => ({ ...prev, phone: e.target.value }))}
                        placeholder="(555) 123-4567"
                        className="w-full pl-10 pr-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                      />
                    </div>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium mb-2">Company</label>
                    <div className="relative">
                      <Building className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-secondary" />
                      <input
                        type="text"
                        value={bookingDetails.company}
                        onChange={e => setBookingDetails(prev => ({ ...prev, company: e.target.value }))}
                        placeholder="Your company"
                        className="w-full pl-10 pr-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                      />
                    </div>
                  </div>
                </div>
                
                {/* Custom questions from meeting type */}
                {selectedType?.questions?.map((q, i) => (
                  <div key={i}>
                    <label className="block text-sm font-medium mb-2">
                      {q.question} {q.required && <span className="text-red-500">*</span>}
                    </label>
                    {q.type === 'textarea' ? (
                      <textarea
                        value={answers[q.id] || ''}
                        onChange={e => setAnswers(prev => ({ ...prev, [q.id]: e.target.value }))}
                        placeholder={q.placeholder}
                        required={q.required}
                        rows={3}
                        className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                      />
                    ) : (
                      <input
                        type={q.type || 'text'}
                        value={answers[q.id] || ''}
                        onChange={e => setAnswers(prev => ({ ...prev, [q.id]: e.target.value }))}
                        placeholder={q.placeholder}
                        required={q.required}
                        className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                      />
                    )}
                  </div>
                ))}
                
                <div>
                  <label className="block text-sm font-medium mb-2">
                    Additional Notes
                  </label>
                  <textarea
                    value={bookingDetails.notes}
                    onChange={e => setBookingDetails(prev => ({ ...prev, notes: e.target.value }))}
                    placeholder="Anything you'd like to share before the meeting..."
                    rows={3}
                    className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
                
                <div className="flex gap-4 pt-4">
                  <button
                    type="button"
                    onClick={() => setStep(2)}
                    className="flex-1 py-3 border border-border rounded-lg font-medium hover:bg-slate-50 transition-colors"
                  >
                    Back
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="flex-1 py-3 bg-primary text-white rounded-lg font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
                  >
                    {isSubmitting ? (
                      <>
                        <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        Booking...
                      </>
                    ) : (
                      <>
                        <Check className="w-5 h-5" />
                        Confirm Booking
                      </>
                    )}
                  </button>
                </div>
              </form>
            </motion.div>
          )}

          {/* Step 4: Confirmation */}
          {step === 4 && confirmedBooking && (
            <motion.div
              key="step4"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="bg-white rounded-2xl shadow-xl p-8 text-center"
            >
              <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
                <Check className="w-10 h-10 text-green-600" />
              </div>
              
              <h2 className="text-2xl font-bold text-foreground mb-2">You&apos;re Booked!</h2>
              <p className="text-secondary mb-8">
                A calendar invitation has been sent to your email
              </p>
              
              <div className="bg-slate-50 rounded-xl p-6 mb-8 text-left">
                <h3 className="font-semibold text-foreground mb-4">{selectedType?.name}</h3>
                <div className="space-y-3 text-sm">
                  <div className="flex items-center gap-3">
                    <User className="w-5 h-5 text-secondary" />
                    <span>with {hostUser?.full_name}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <Calendar className="w-5 h-5 text-secondary" />
                    <span>{selectedTime && format(parseISO(selectedTime), 'EEEE, MMMM d, yyyy')}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <Clock className="w-5 h-5 text-secondary" />
                    <span>{selectedTime && format(parseISO(selectedTime), 'h:mm a')} ({selectedType?.duration} min)</span>
                  </div>
                  {confirmedBooking.meeting_link && (
                    <div className="flex items-center gap-3">
                      <Video className="w-5 h-5 text-secondary" />
                      <a 
                        href={confirmedBooking.meeting_link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary hover:underline flex items-center gap-1"
                      >
                        Join Meeting
                        <ExternalLink className="w-4 h-4" />
                      </a>
                    </div>
                  )}
                </div>
              </div>
              
              <div className="flex gap-4">
                <a
                  href={`https://calendar.google.com/calendar/render?action=TEMPLATE&text=${encodeURIComponent(selectedType?.name + ' with ' + hostUser?.full_name)}&dates=${selectedTime ? format(parseISO(selectedTime), "yyyyMMdd'T'HHmmss") : ''}/${selectedTime ? format(new Date(parseISO(selectedTime).getTime() + selectedType?.duration * 60000), "yyyyMMdd'T'HHmmss") : ''}&details=${encodeURIComponent('Meeting link: ' + confirmedBooking.meeting_link)}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 py-3 border border-border rounded-lg font-medium hover:bg-slate-50 transition-colors flex items-center justify-center gap-2"
                >
                  <Calendar className="w-5 h-5" />
                  Add to Google Calendar
                </a>
                <button
                  onClick={() => window.location.reload()}
                  className="flex-1 py-3 bg-primary text-white rounded-lg font-medium hover:bg-primary/90 transition-colors"
                >
                  Book Another
                </button>
              </div>
              
              <p className="text-xs text-secondary mt-6">
                <Sparkles className="w-4 h-4 inline mr-1" />
                Powered by LeadGen Pro
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default BookingPageEnhanced;
