import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { 
  Phone, PhoneOff, PhoneCall, Clock, User, Building,
  CheckCircle, X, MessageSquare, Voicemail, PhoneMissed
} from 'lucide-react';
import { toast } from 'react-toastify';
import { motion, AnimatePresence } from 'framer-motion';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const CallModal = ({ isOpen, onClose, lead, onCallLogged }) => {
  const [callState, setCallState] = useState('idle'); // idle, calling, connected, ended
  const [callSid, setCallSid] = useState(null);
  const [duration, setDuration] = useState(0);
  const [outcome, setOutcome] = useState('');
  const [notes, setNotes] = useState('');
  const [isLogging, setIsLogging] = useState(false);

  // Timer for call duration
  useEffect(() => {
    let interval;
    if (callState === 'connected') {
      interval = setInterval(() => {
        setDuration(prev => prev + 1);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [callState]);

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setCallState('idle');
      setCallSid(null);
      setDuration(0);
      setOutcome('');
      setNotes('');
    }
  }, [isOpen]);

  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const initiateCall = async () => {
    if (!lead?.phone) {
      toast.error('No phone number available for this lead');
      return;
    }

    setCallState('calling');
    
    try {
      const response = await axios.post(`${API_URL}/api/voice/call`, null, {
        params: {
          phone_number: lead.phone,
          lead_id: lead.id
        }
      });

      if (response.data.success) {
        setCallSid(response.data.call_sid);
        setCallState('connected');
        toast.success('Call connected!');
      } else {
        setCallState('idle');
        toast.error('Failed to initiate call');
      }
    } catch (error) {
      console.error('Call error:', error);
      setCallState('idle');
      toast.error(error.response?.data?.detail || 'Failed to initiate call');
    }
  };

  const endCall = async () => {
    if (callSid) {
      try {
        await axios.post(`${API_URL}/api/voice/call/${callSid}/end`);
      } catch (error) {
        console.error('Error ending call:', error);
      }
    }
    setCallState('ended');
  };

  const logCall = async () => {
    if (!outcome) {
      toast.error('Please select a call outcome');
      return;
    }

    setIsLogging(true);

    try {
      await axios.post(`${API_URL}/api/calls/log`, {
        lead_id: lead.id,
        phone_number: lead.phone,
        outcome: outcome,
        duration: duration,
        notes: notes,
        call_sid: callSid
      });

      toast.success('Call logged successfully!');
      if (onCallLogged) onCallLogged();
      onClose();
    } catch (error) {
      console.error('Error logging call:', error);
      toast.error('Failed to log call');
    } finally {
      setIsLogging(false);
    }
  };

  const outcomeOptions = [
    { value: 'connected', label: 'Connected - Spoke with contact', icon: CheckCircle, color: 'text-green-600' },
    { value: 'voicemail', label: 'Voicemail - Left message', icon: Voicemail, color: 'text-blue-600' },
    { value: 'no_answer', label: 'No Answer', icon: PhoneMissed, color: 'text-yellow-600' },
    { value: 'busy', label: 'Busy Signal', icon: Phone, color: 'text-orange-600' },
    { value: 'wrong_number', label: 'Wrong Number', icon: X, color: 'text-red-600' },
    { value: 'declined', label: 'Declined to speak', icon: PhoneOff, color: 'text-gray-600' }
  ];

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
        onClick={(e) => e.target === e.currentTarget && callState !== 'connected' && onClose()}
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          className="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden"
        >
          {/* Header */}
          <div className={`p-6 ${callState === 'connected' ? 'bg-green-500' : callState === 'calling' ? 'bg-blue-500' : 'bg-primary'} text-white`}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold">
                {callState === 'idle' && 'Call Lead'}
                {callState === 'calling' && 'Calling...'}
                {callState === 'connected' && 'Call in Progress'}
                {callState === 'ended' && 'Call Ended'}
              </h2>
              {callState !== 'connected' && (
                <button onClick={onClose} className="p-1 hover:bg-white/20 rounded-full transition-colors">
                  <X className="w-5 h-5" />
                </button>
              )}
            </div>

            {/* Lead Info */}
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-full bg-white/20 flex items-center justify-center">
                <User className="w-7 h-7" />
              </div>
              <div>
                <h3 className="font-semibold text-lg">
                  {lead?.first_name} {lead?.last_name}
                </h3>
                <p className="text-white/80 text-sm flex items-center gap-1">
                  <Building className="w-4 h-4" />
                  {lead?.company}
                </p>
                <p className="text-white/80 text-sm flex items-center gap-1">
                  <Phone className="w-4 h-4" />
                  {lead?.phone || 'No phone number'}
                </p>
              </div>
            </div>

            {/* Duration Display */}
            {(callState === 'connected' || callState === 'ended') && (
              <div className="mt-4 flex items-center justify-center gap-2 text-2xl font-mono">
                <Clock className="w-6 h-6" />
                {formatDuration(duration)}
              </div>
            )}
          </div>

          {/* Body */}
          <div className="p-6">
            {/* Idle State - Show Call Button */}
            {callState === 'idle' && (
              <div className="text-center">
                <p className="text-secondary mb-6">Click the button below to initiate a call</p>
                <button
                  onClick={initiateCall}
                  disabled={!lead?.phone}
                  className="w-full py-4 bg-green-500 hover:bg-green-600 text-white rounded-xl font-semibold flex items-center justify-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <PhoneCall className="w-5 h-5" />
                  Start Call
                </button>
              </div>
            )}

            {/* Calling State */}
            {callState === 'calling' && (
              <div className="text-center py-8">
                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-blue-100 flex items-center justify-center animate-pulse">
                  <Phone className="w-8 h-8 text-blue-600" />
                </div>
                <p className="text-secondary">Connecting to {lead?.phone}...</p>
              </div>
            )}

            {/* Connected State - Show End Call Button */}
            {callState === 'connected' && (
              <div className="text-center">
                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-green-100 flex items-center justify-center">
                  <PhoneCall className="w-8 h-8 text-green-600 animate-pulse" />
                </div>
                <p className="text-secondary mb-6">Call in progress with {lead?.first_name}</p>
                <button
                  onClick={endCall}
                  className="w-full py-4 bg-red-500 hover:bg-red-600 text-white rounded-xl font-semibold flex items-center justify-center gap-2 transition-colors"
                >
                  <PhoneOff className="w-5 h-5" />
                  End Call
                </button>
              </div>
            )}

            {/* Ended State - Show Logging Form */}
            {callState === 'ended' && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">Call Outcome *</label>
                  <div className="grid grid-cols-2 gap-2">
                    {outcomeOptions.map((opt) => {
                      const Icon = opt.icon;
                      return (
                        <button
                          key={opt.value}
                          onClick={() => setOutcome(opt.value)}
                          className={`p-3 rounded-lg border-2 text-left transition-all ${
                            outcome === opt.value 
                              ? 'border-primary bg-primary/5' 
                              : 'border-border hover:border-primary/50'
                          }`}
                        >
                          <div className="flex items-center gap-2">
                            <Icon className={`w-4 h-4 ${opt.color}`} />
                            <span className="text-xs font-medium">{opt.label}</span>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    <MessageSquare className="w-4 h-4 inline mr-1" />
                    Notes
                  </label>
                  <textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Add any notes about the call..."
                    className="w-full p-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary resize-none"
                    rows={3}
                  />
                </div>

                <div className="flex gap-3 pt-2">
                  <button
                    onClick={onClose}
                    className="flex-1 py-3 border border-border rounded-xl font-medium hover:bg-slate-50 transition-colors"
                  >
                    Skip Logging
                  </button>
                  <button
                    onClick={logCall}
                    disabled={isLogging || !outcome}
                    className="flex-1 py-3 bg-primary text-white rounded-xl font-semibold hover:bg-primary/90 transition-colors disabled:opacity-50"
                  >
                    {isLogging ? 'Logging...' : 'Log Call'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default CallModal;
