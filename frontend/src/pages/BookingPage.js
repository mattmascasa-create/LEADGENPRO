import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import { 
  Calendar, Clock, User, Building, Mail, Phone, 
  ChevronLeft, ChevronRight, Check, Sparkles
} from 'lucide-react';
import { toast } from 'react-toastify';
import { format, addDays, startOfWeek, addWeeks, isSameDay, setHours, setMinutes, isAfter, isBefore } from 'date-fns';
import { motion } from 'framer-motion';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const BookingPage = () => {
  const { userId } = useParams();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [step, setStep] = useState(1); // 1: Select Date, 2: Select Time, 3: Enter Details, 4: Confirmed
  const [selectedDate, setSelectedDate] = useState(null);
  const [selectedTime, setSelectedTime] = useState(null);
  const [currentWeekStart, setCurrentWeekStart] = useState(startOfWeek(new Date(), { weekStartsOn: 1 }));
  const [availableSlots, setAvailableSlots] = useState([]);
  const [bookedSlots, setBookedSlots] = useState([]);
  const [bookingDetails, setBookingDetails] = useState({
    name: '',
    email: '',
    phone: '',
    company: '',
    notes: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [confirmedBooking, setConfirmedBooking] = useState(null);

  useEffect(() => {
    fetchUserAndAvailability();
  }, [userId]);

  useEffect(() => {
    if (selectedDate) {
      fetchAvailableSlots(selectedDate);
    }
  }, [selectedDate]);

  const fetchUserAndAvailability = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/booking/${userId}`);
      setUser(response.data.user);
      setBookedSlots(response.data.booked_slots || []);
    } catch (error) {
      toast.error('Failed to load booking page');
    } finally {
      setLoading(false);
    }
  };

  const fetchAvailableSlots = async (date) => {
    try {
      const response = await axios.get(`${API_URL}/api/booking/${userId}/slots`, {
        params: { date: format(date, 'yyyy-MM-dd') }
      });
      setAvailableSlots(response.data.slots);
    } catch (error) {
      console.error('Failed to fetch slots:', error);
      // Generate default slots if API fails
      generateDefaultSlots(date);
    }
  };

  const generateDefaultSlots = (date) => {
    const slots = [];
    const now = new Date();
    
    // Business hours: 9 AM to 5 PM, 30-minute slots
    for (let hour = 9; hour < 17; hour++) {
      for (let min = 0; min < 60; min += 30) {
        const slotTime = setMinutes(setHours(new Date(date), hour), min);
        
        // Skip past times for today
        if (isSameDay(date, now) && isBefore(slotTime, now)) {
          continue;
        }
        
        // Check if slot is already booked
        const isBooked = bookedSlots.some(booked => 
          isSameDay(new Date(booked), slotTime) && 
          format(new Date(booked), 'HH:mm') === format(slotTime, 'HH:mm')
        );
        
        if (!isBooked) {
          slots.push(format(slotTime, 'HH:mm'));
        }
      }
    }
    setAvailableSlots(slots);
  };

  const handleBooking = async (e) => {
    e.preventDefault();
    
    if (!bookingDetails.name || !bookingDetails.email) {
      toast.error('Please fill in your name and email');
      return;
    }

    setIsSubmitting(true);

    try {
      const bookingDateTime = setMinutes(
        setHours(new Date(selectedDate), parseInt(selectedTime.split(':')[0])),
        parseInt(selectedTime.split(':')[1])
      );

      const response = await axios.post(`${API_URL}/api/booking/${userId}/book`, {
        ...bookingDetails,
        datetime: bookingDateTime.toISOString(),
        duration: 30 // 30-minute meeting
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

  // Generate week days
  const weekDays = Array.from({ length: 7 }, (_, i) => addDays(currentWeekStart, i));
  const today = new Date();

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-primary text-xl">Loading...</div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-2">Booking Not Found</h1>
          <p className="text-secondary">This booking link may be invalid or expired.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      {/* Header */}
      <header className="bg-white border-b border-border py-4 px-6">
        <div className="max-w-4xl mx-auto flex items-center gap-3">
          <div className="w-10 h-10 bg-primary rounded-lg flex items-center justify-center">
            <Sparkles className="w-6 h-6 text-white" />
          </div>
          <span className="text-xl font-bold">LeadGen Pro</span>
        </div>
      </header>

      <div className="max-w-4xl mx-auto py-12 px-6">
        <div className="bg-white rounded-2xl shadow-xl overflow-hidden">
          <div className="grid md:grid-cols-3">
            {/* Left Panel - User Info */}
            <div className="bg-primary p-8 text-white">
              <div className="w-20 h-20 bg-white/20 rounded-full flex items-center justify-center mb-6">
                <User className="w-10 h-10" />
              </div>
              <h1 className="text-2xl font-bold mb-2">{user.full_name}</h1>
              <p className="text-white/80 mb-6">{user.company || 'LeadGen Pro'}</p>
              
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <Clock className="w-5 h-5 text-white/60" />
                  <span>30 min meeting</span>
                </div>
                <div className="flex items-center gap-3">
                  <Calendar className="w-5 h-5 text-white/60" />
                  <span>Video or Phone Call</span>
                </div>
              </div>

              {selectedDate && selectedTime && (
                <div className="mt-8 p-4 bg-white/10 rounded-lg">
                  <p className="text-sm text-white/60 mb-1">Selected Time</p>
                  <p className="font-semibold">{format(selectedDate, 'EEEE, MMMM d')}</p>
                  <p className="text-lg">{selectedTime}</p>
                </div>
              )}
            </div>

            {/* Right Panel - Booking Flow */}
            <div className="md:col-span-2 p-8">
              {/* Step 1: Select Date */}
              {step === 1 && (
                <motion.div
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                >
                  <h2 className="text-2xl font-bold mb-6">Select a Date</h2>
                  
                  {/* Week Navigation */}
                  <div className="flex items-center justify-between mb-6">
                    <button
                      onClick={() => setCurrentWeekStart(addWeeks(currentWeekStart, -1))}
                      disabled={isBefore(currentWeekStart, today)}
                      className="p-2 hover:bg-slate-100 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <ChevronLeft className="w-5 h-5" />
                    </button>
                    <span className="font-medium">
                      {format(currentWeekStart, 'MMMM yyyy')}
                    </span>
                    <button
                      onClick={() => setCurrentWeekStart(addWeeks(currentWeekStart, 1))}
                      className="p-2 hover:bg-slate-100 rounded-lg"
                    >
                      <ChevronRight className="w-5 h-5" />
                    </button>
                  </div>

                  {/* Week Grid */}
                  <div className="grid grid-cols-7 gap-2 mb-6">
                    {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map(day => (
                      <div key={day} className="text-center text-sm font-medium text-secondary py-2">
                        {day}
                      </div>
                    ))}
                    {weekDays.map((day, idx) => {
                      const isPast = isBefore(day, today) && !isSameDay(day, today);
                      const isWeekend = idx >= 5;
                      const isSelected = selectedDate && isSameDay(day, selectedDate);
                      
                      return (
                        <button
                          key={idx}
                          onClick={() => {
                            setSelectedDate(day);
                            setStep(2);
                          }}
                          disabled={isPast || isWeekend}
                          className={`p-4 rounded-lg text-center transition-all ${
                            isSelected
                              ? 'bg-primary text-white'
                              : isPast || isWeekend
                              ? 'bg-slate-50 text-slate-300 cursor-not-allowed'
                              : 'bg-slate-50 hover:bg-primary/10 hover:border-primary border-2 border-transparent'
                          }`}
                        >
                          <span className="text-lg font-semibold">{format(day, 'd')}</span>
                        </button>
                      );
                    })}
                  </div>

                  <button
                    onClick={() => setCurrentWeekStart(addWeeks(currentWeekStart, 1))}
                    className="w-full py-3 text-primary font-medium hover:bg-primary/5 rounded-lg transition-colors"
                  >
                    View Next Week →
                  </button>
                </motion.div>
              )}

              {/* Step 2: Select Time */}
              {step === 2 && (
                <motion.div
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                >
                  <button
                    onClick={() => setStep(1)}
                    className="flex items-center gap-2 text-secondary hover:text-foreground mb-4"
                  >
                    <ChevronLeft className="w-4 h-4" />
                    Back to calendar
                  </button>

                  <h2 className="text-2xl font-bold mb-2">Select a Time</h2>
                  <p className="text-secondary mb-6">
                    {format(selectedDate, 'EEEE, MMMM d, yyyy')}
                  </p>

                  <div className="grid grid-cols-3 gap-3 max-h-80 overflow-y-auto">
                    {availableSlots.length > 0 ? (
                      availableSlots.map((slot) => (
                        <button
                          key={slot}
                          onClick={() => {
                            setSelectedTime(slot);
                            setStep(3);
                          }}
                          className={`py-3 px-4 rounded-lg border-2 font-medium transition-all ${
                            selectedTime === slot
                              ? 'border-primary bg-primary text-white'
                              : 'border-border hover:border-primary hover:bg-primary/5'
                          }`}
                        >
                          {slot}
                        </button>
                      ))
                    ) : (
                      <p className="col-span-3 text-center text-secondary py-8">
                        No available slots for this day
                      </p>
                    )}
                  </div>
                </motion.div>
              )}

              {/* Step 3: Enter Details */}
              {step === 3 && (
                <motion.div
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                >
                  <button
                    onClick={() => setStep(2)}
                    className="flex items-center gap-2 text-secondary hover:text-foreground mb-4"
                  >
                    <ChevronLeft className="w-4 h-4" />
                    Back to time selection
                  </button>

                  <h2 className="text-2xl font-bold mb-6">Enter Your Details</h2>

                  <form onSubmit={handleBooking} className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium mb-1">Your Name *</label>
                      <input
                        type="text"
                        value={bookingDetails.name}
                        onChange={(e) => setBookingDetails({...bookingDetails, name: e.target.value})}
                        required
                        className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                        placeholder="John Doe"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-1">Email *</label>
                      <input
                        type="email"
                        value={bookingDetails.email}
                        onChange={(e) => setBookingDetails({...bookingDetails, email: e.target.value})}
                        required
                        className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                        placeholder="john@company.com"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-1">Phone</label>
                      <input
                        type="tel"
                        value={bookingDetails.phone}
                        onChange={(e) => setBookingDetails({...bookingDetails, phone: e.target.value})}
                        className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                        placeholder="+1 (555) 000-0000"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-1">Company</label>
                      <input
                        type="text"
                        value={bookingDetails.company}
                        onChange={(e) => setBookingDetails({...bookingDetails, company: e.target.value})}
                        className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                        placeholder="Acme Inc."
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-1">Additional Notes</label>
                      <textarea
                        value={bookingDetails.notes}
                        onChange={(e) => setBookingDetails({...bookingDetails, notes: e.target.value})}
                        rows={3}
                        className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary resize-none"
                        placeholder="Anything you'd like to discuss..."
                      />
                    </div>

                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="w-full py-4 bg-primary text-white rounded-lg font-semibold hover:bg-primary/90 transition-colors disabled:opacity-50"
                    >
                      {isSubmitting ? 'Scheduling...' : 'Schedule Meeting'}
                    </button>
                  </form>
                </motion.div>
              )}

              {/* Step 4: Confirmed */}
              {step === 4 && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="text-center py-8"
                >
                  <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
                    <Check className="w-10 h-10 text-green-600" />
                  </div>
                  <h2 className="text-3xl font-bold mb-4">You're All Set!</h2>
                  <p className="text-secondary mb-8">
                    Your meeting has been scheduled. {user.full_name} has been notified.
                  </p>

                  <div className="bg-slate-50 rounded-xl p-6 text-left max-w-sm mx-auto">
                    <h3 className="font-semibold mb-4">Meeting Details</h3>
                    <div className="space-y-3 text-sm">
                      <div className="flex items-center gap-3">
                        <Calendar className="w-5 h-5 text-primary" />
                        <span>{format(selectedDate, 'EEEE, MMMM d, yyyy')}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <Clock className="w-5 h-5 text-primary" />
                        <span>{selectedTime} (30 minutes)</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <User className="w-5 h-5 text-primary" />
                        <span>with {user.full_name}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <Mail className="w-5 h-5 text-primary" />
                        <span>Confirmation sent to {bookingDetails.email}</span>
                      </div>
                    </div>
                  </div>

                  <div className="bg-green-50 border border-green-200 rounded-xl p-4 max-w-sm mx-auto mt-6">
                    <p className="text-sm text-green-800">
                      <strong>What's next?</strong> Check your email for meeting details and preparation tips.
                    </p>
                  </div>
                </motion.div>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <p className="text-center text-sm text-secondary mt-8">
          Powered by LeadGen Pro
        </p>
      </div>
    </div>
  );
};

export default BookingPage;
