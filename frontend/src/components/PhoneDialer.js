import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import { 
  Phone, PhoneOff, Mic, MicOff, Volume2, VolumeX, 
  Delete, X, Loader2, Clock, User, Circle, PhoneCall,
  PhoneIncoming, PhoneMissed, CheckCircle, AlertCircle,
  FileText, Save, MessageSquare, Settings, Info
} from 'lucide-react';
import { toast } from 'react-toastify';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '@/context/AuthContext';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const PhoneDialer = ({ isOpen, onClose, prefilledNumber = '', leadInfo = null }) => {
  const { user, refreshUser } = useAuth();
  const [phoneNumber, setPhoneNumber] = useState(prefilledNumber);
  const [agentPhone, setAgentPhone] = useState('');
  const [showSettings, setShowSettings] = useState(false);
  const [savingPhone, setSavingPhone] = useState(false);
  const [isCallActive, setIsCallActive] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [isSpeakerOn, setIsSpeakerOn] = useState(true);
  const [isRecording, setIsRecording] = useState(true);
  const [callDuration, setCallDuration] = useState(0);
  const [callStatus, setCallStatus] = useState('idle'); // idle, calling_agent, connecting, connected, ended, failed
  const [callSid, setCallSid] = useState(null);
  const [callId, setCallId] = useState(null);
  const [showOutcomeModal, setShowOutcomeModal] = useState(false);
  const [callNotes, setCallNotes] = useState('');
  const [selectedOutcome, setSelectedOutcome] = useState('');
  const [savingOutcome, setSavingOutcome] = useState(false);
  const [recentCalls, setRecentCalls] = useState([]);
  const [showRecentCalls, setShowRecentCalls] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');
  
  const timerRef = useRef(null);
  const statusPollRef = useRef(null);

  useEffect(() => {
    if (prefilledNumber) {
      setPhoneNumber(prefilledNumber);
    }
  }, [prefilledNumber]);

  useEffect(() => {
    if (user?.phone) {
      setAgentPhone(user.phone);
    }
  }, [user]);

  useEffect(() => {
    if (isOpen) {
      fetchRecentCalls();
      // Check if user has phone set
      if (!user?.phone) {
        setShowSettings(true);
      }
    }
  }, [isOpen, user]);

  useEffect(() => {
    if (callStatus === 'connected' || callStatus === 'connecting') {
      timerRef.current = setInterval(() => {
        setCallDuration(prev => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    }
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [callStatus]);

  useEffect(() => {
    return () => {
      if (statusPollRef.current) {
        clearInterval(statusPollRef.current);
      }
    };
  }, []);

  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const formatPhoneDisplay = (number) => {
    const digits = number.replace(/\D/g, '');
    if (digits.length === 10) {
      return `(${digits.slice(0,3)}) ${digits.slice(3,6)}-${digits.slice(6)}`;
    } else if (digits.length === 11 && digits.startsWith('1')) {
      return `+1 (${digits.slice(1,4)}) ${digits.slice(4,7)}-${digits.slice(7)}`;
    }
    return number;
  };

  const dialPadButtons = [
    [{ digit: '1', letters: '' }, { digit: '2', letters: 'ABC' }, { digit: '3', letters: 'DEF' }],
    [{ digit: '4', letters: 'GHI' }, { digit: '5', letters: 'JKL' }, { digit: '6', letters: 'MNO' }],
    [{ digit: '7', letters: 'PQRS' }, { digit: '8', letters: 'TUV' }, { digit: '9', letters: 'WXYZ' }],
    [{ digit: '*', letters: '' }, { digit: '0', letters: '+' }, { digit: '#', letters: '' }]
  ];

  const callOutcomes = [
    { id: 'connected', label: 'Connected', description: 'Spoke with contact', icon: CheckCircle, color: 'text-green-500' },
    { id: 'voicemail', label: 'Voicemail', description: 'Left a message', icon: MessageSquare, color: 'text-blue-500' },
    { id: 'no_answer', label: 'No Answer', description: 'No response', icon: PhoneMissed, color: 'text-yellow-500' },
    { id: 'busy', label: 'Busy', description: 'Line was busy', icon: PhoneOff, color: 'text-orange-500' },
    { id: 'wrong_number', label: 'Wrong Number', description: 'Incorrect contact', icon: AlertCircle, color: 'text-red-500' },
    { id: 'declined', label: 'Declined', description: 'Contact declined', icon: X, color: 'text-slate-500' }
  ];

  const handleDigitPress = (digit) => {
    if (phoneNumber.length < 15) {
      setPhoneNumber(prev => prev + digit);
    }
  };

  const handleBackspace = () => {
    setPhoneNumber(prev => prev.slice(0, -1));
  };

  const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return { headers: { Authorization: `Bearer ${token}` } };
  };

  const fetchRecentCalls = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/calls/logs?limit=5`, getAuthHeaders());
      setRecentCalls(response.data);
    } catch (error) {
      console.error('Failed to fetch recent calls');
    }
  };

  const saveAgentPhone = async () => {
    if (!agentPhone || agentPhone.replace(/\D/g, '').length < 10) {
      toast.error('Please enter a valid 10-digit phone number');
      return;
    }

    setSavingPhone(true);
    try {
      await axios.put(
        `${API_URL}/api/auth/profile`,
        { phone: agentPhone },
        getAuthHeaders()
      );
      toast.success('Phone number saved! You can now make calls.');
      setShowSettings(false);
      if (refreshUser) refreshUser();
    } catch (error) {
      toast.error('Failed to save phone number');
    } finally {
      setSavingPhone(false);
    }
  };

  const initiateCall = async () => {
    if (!phoneNumber || phoneNumber.replace(/\D/g, '').length < 10) {
      toast.error('Please enter a valid 10-digit phone number');
      return;
    }

    const effectiveAgentPhone = agentPhone || user?.phone;
    if (!effectiveAgentPhone) {
      toast.error('Please set your phone number first');
      setShowSettings(true);
      return;
    }

    setCallStatus('calling_agent');
    setStatusMessage('Calling your phone...');
    setIsCallActive(true);
    setCallDuration(0);

    try {
      const response = await axios.post(
        `${API_URL}/api/voice/call`,
        {
          to_number: phoneNumber,
          lead_id: leadInfo?.id || null,
          record: isRecording,
          agent_phone: effectiveAgentPhone
        },
        getAuthHeaders()
      );

      if (response.data.success) {
        setCallSid(response.data.call_sid);
        setCallId(response.data.call_id);
        toast.info('📞 Calling your phone - answer and press 1 to connect!');
        setStatusMessage('Answer your phone and press 1');
        
        // Start polling for call status
        startStatusPolling(response.data.call_id);
      } else {
        throw new Error(response.data.message || 'Failed to initiate call');
      }
    } catch (error) {
      console.error('Call error:', error);
      const errorMsg = error.response?.data?.detail || 'Failed to initiate call';
      toast.error(errorMsg);
      setCallStatus('failed');
      setStatusMessage('Call failed');
      setTimeout(() => {
        setCallStatus('idle');
        setIsCallActive(false);
        setStatusMessage('');
      }, 2000);
    }
  };

  const startStatusPolling = (cid) => {
    let attempts = 0;
    const maxAttempts = 120;
    
    statusPollRef.current = setInterval(async () => {
      try {
        // Check pending call status
        const response = await axios.get(
          `${API_URL}/api/voice/pending/${cid}`,
          getAuthHeaders()
        );
        
        const status = response.data.status;
        
        if (status === 'connecting_to_lead') {
          setCallStatus('connecting');
          setStatusMessage('Connecting to lead...');
        } else if (status === 'connected' || status === 'in-progress') {
          setCallStatus('connected');
          setStatusMessage('Call connected');
          toast.success('📞 Connected!');
        } else if (status === 'completed') {
          clearInterval(statusPollRef.current);
          handleCallEnded(response.data.duration || callDuration, 'completed');
        } else if (status === 'agent_no_answer') {
          clearInterval(statusPollRef.current);
          toast.warning('You didn\'t answer your phone');
          handleCallEnded(0, 'no_answer');
        }
        
        attempts++;
        if (attempts >= maxAttempts) {
          clearInterval(statusPollRef.current);
        }
      } catch (error) {
        // Call might have ended normally
        attempts++;
        if (attempts >= maxAttempts) {
          clearInterval(statusPollRef.current);
        }
      }
    }, 2000);
  };

  const handleCallEnded = (duration, outcome) => {
    if (statusPollRef.current) {
      clearInterval(statusPollRef.current);
    }
    
    setCallStatus('ended');
    setStatusMessage('Call ended');
    
    setTimeout(() => {
      setSelectedOutcome(outcome === 'completed' ? '' : outcome);
      setShowOutcomeModal(true);
    }, 1000);
  };

  const endCall = async () => {
    if (statusPollRef.current) {
      clearInterval(statusPollRef.current);
    }
    
    if (callSid) {
      try {
        await axios.post(
          `${API_URL}/api/voice/hangup`,
          { call_sid: callSid },
          getAuthHeaders()
        );
        toast.info('📞 Call ended');
      } catch (error) {
        console.error('Hangup error:', error);
      }
    }
    
    handleCallEnded(callDuration, 'connected');
  };

  const saveCallOutcome = async () => {
    if (!selectedOutcome) {
      toast.error('Please select a call outcome');
      return;
    }

    setSavingOutcome(true);
    try {
      await axios.post(
        `${API_URL}/api/calls/log`,
        {
          lead_id: leadInfo?.id || null,
          phone_number: phoneNumber,
          outcome: selectedOutcome,
          duration: callDuration,
          call_sid: callSid,
          notes: callNotes
        },
        getAuthHeaders()
      );
      
      toast.success('✅ Call logged!');
      setShowOutcomeModal(false);
      resetDialer();
      fetchRecentCalls();
    } catch (error) {
      toast.error('Failed to save');
    } finally {
      setSavingOutcome(false);
    }
  };

  const skipOutcomeLog = () => {
    setShowOutcomeModal(false);
    resetDialer();
  };

  const resetDialer = () => {
    setCallStatus('idle');
    setIsCallActive(false);
    setCallSid(null);
    setCallId(null);
    setCallDuration(0);
    setCallNotes('');
    setSelectedOutcome('');
    setStatusMessage('');
  };

  const redialNumber = (number) => {
    setPhoneNumber(number);
    setShowRecentCalls(false);
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4"
        onClick={(e) => e.target === e.currentTarget && !isCallActive && !showOutcomeModal && onClose()}
      >
        <motion.div
          initial={{ scale: 0.9, y: 20 }}
          animate={{ scale: 1, y: 0 }}
          exit={{ scale: 0.9, y: 20 }}
          className="bg-gradient-to-b from-slate-900 via-slate-800 to-slate-900 rounded-3xl shadow-2xl w-full max-w-sm overflow-hidden border border-slate-700/50"
          data-testid="phone-dialer"
        >
          {/* Header */}
          <div className="p-5 text-center relative">
            {!isCallActive && !showOutcomeModal && (
              <div className="absolute right-4 top-4 flex gap-2">
                <button
                  onClick={() => setShowSettings(!showSettings)}
                  className={`p-2 rounded-full transition-all ${showSettings ? 'bg-primary text-white' : 'text-slate-400 hover:text-white hover:bg-slate-700/50'}`}
                  title="Settings"
                >
                  <Settings className="w-5 h-5" />
                </button>
                <button
                  onClick={onClose}
                  className="p-2 text-slate-400 hover:text-white hover:bg-slate-700/50 rounded-full transition-all"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            )}
            
            {/* Lead Info */}
            {leadInfo && !showSettings && (
              <div className="mb-4">
                <div className="w-16 h-16 bg-gradient-to-br from-primary to-blue-600 rounded-full flex items-center justify-center mx-auto mb-2 shadow-lg shadow-primary/30">
                  <User className="w-8 h-8 text-white" />
                </div>
                <p className="text-white font-semibold text-lg">{leadInfo.first_name} {leadInfo.last_name}</p>
                <p className="text-slate-400 text-sm">{leadInfo.company}</p>
              </div>
            )}

            {!leadInfo && !isCallActive && !showSettings && (
              <div className="mb-2">
                <div className="w-14 h-14 bg-gradient-to-br from-green-500 to-emerald-600 rounded-full flex items-center justify-center mx-auto mb-2 shadow-lg shadow-green-500/30">
                  <Phone className="w-7 h-7 text-white" />
                </div>
                <h2 className="text-white font-semibold text-lg">Click-to-Call</h2>
                <p className="text-slate-500 text-xs mt-1">We'll call your phone, then connect you</p>
              </div>
            )}

            {/* Settings Panel */}
            {showSettings && !isCallActive && (
              <div className="text-left mt-8">
                <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
                  <Settings className="w-5 h-5 text-primary" />
                  Your Phone Number
                </h3>
                <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50 mb-4">
                  <div className="flex items-start gap-2 mb-3">
                    <Info className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
                    <p className="text-slate-400 text-xs">
                      When you make a call, we'll ring your phone first. Answer and press 1 to connect to the lead.
                    </p>
                  </div>
                  <input
                    type="tel"
                    value={agentPhone}
                    onChange={(e) => setAgentPhone(e.target.value.replace(/[^\d+\-\s()]/g, ''))}
                    placeholder="Your phone number"
                    className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-xl text-white placeholder-slate-500 mb-3"
                  />
                  <button
                    onClick={saveAgentPhone}
                    disabled={savingPhone}
                    className="w-full py-3 bg-primary text-white rounded-xl font-medium hover:bg-primary/90 disabled:opacity-50 flex items-center justify-center gap-2"
                  >
                    {savingPhone ? <Loader2 className="w-5 h-5 animate-spin" /> : <Save className="w-5 h-5" />}
                    Save Phone Number
                  </button>
                </div>
                {user?.phone && (
                  <p className="text-green-400 text-sm text-center">
                    ✓ Your phone: {formatPhoneDisplay(user.phone)}
                  </p>
                )}
              </div>
            )}

            {/* Call Status Display */}
            {callStatus === 'calling_agent' && (
              <div className="py-4">
                <motion.div
                  animate={{ scale: [1, 1.1, 1] }}
                  transition={{ repeat: Infinity, duration: 1.5 }}
                  className="w-16 h-16 bg-blue-500/20 rounded-full flex items-center justify-center mx-auto mb-3"
                >
                  <PhoneIncoming className="w-8 h-8 text-blue-400" />
                </motion.div>
                <p className="text-blue-400 font-medium">Calling Your Phone</p>
                <p className="text-slate-500 text-sm mt-1">{statusMessage}</p>
                <p className="text-slate-400 text-xs mt-2">Answer and press 1 to connect</p>
              </div>
            )}

            {callStatus === 'connecting' && (
              <div className="py-4">
                <motion.div
                  animate={{ scale: [1, 1.1, 1] }}
                  transition={{ repeat: Infinity, duration: 1.5 }}
                  className="w-16 h-16 bg-yellow-500/20 rounded-full flex items-center justify-center mx-auto mb-3"
                >
                  <PhoneCall className="w-8 h-8 text-yellow-400" />
                </motion.div>
                <p className="text-yellow-400 font-medium">Connecting to Lead</p>
                <p className="text-slate-500 text-sm">{formatPhoneDisplay(phoneNumber)}</p>
                <div className="flex items-center justify-center gap-2 mt-2 text-white text-xl font-mono">
                  <Clock className="w-5 h-5 text-slate-400" />
                  {formatDuration(callDuration)}
                </div>
              </div>
            )}

            {callStatus === 'connected' && (
              <div className="py-4">
                <div className="flex items-center justify-center gap-2 mb-3">
                  <motion.div
                    animate={{ scale: [1, 1.2, 1] }}
                    transition={{ repeat: Infinity, duration: 1 }}
                  >
                    <Circle className="w-3 h-3 text-green-500 fill-green-500" />
                  </motion.div>
                  <span className="text-green-400 font-semibold">Connected</span>
                </div>
                <div className="flex items-center justify-center gap-2 text-white text-4xl font-mono mb-2">
                  {formatDuration(callDuration)}
                </div>
                <p className="text-slate-400 text-sm">{formatPhoneDisplay(phoneNumber)}</p>
                {isRecording && (
                  <div className="flex items-center justify-center gap-1.5 mt-3 text-red-400 text-sm">
                    <Circle className="w-2 h-2 fill-red-500 animate-pulse" />
                    Recording
                  </div>
                )}
              </div>
            )}

            {callStatus === 'ended' && !showOutcomeModal && (
              <div className="py-4">
                <div className="w-14 h-14 bg-slate-700 rounded-full flex items-center justify-center mx-auto mb-3">
                  <PhoneOff className="w-7 h-7 text-slate-400" />
                </div>
                <p className="text-slate-300 font-medium">Call Ended</p>
                <p className="text-slate-500 text-sm">Duration: {formatDuration(callDuration)}</p>
              </div>
            )}

            {callStatus === 'failed' && (
              <div className="py-4">
                <div className="w-14 h-14 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-3">
                  <AlertCircle className="w-7 h-7 text-red-400" />
                </div>
                <p className="text-red-400 font-medium">Call Failed</p>
                <p className="text-slate-500 text-sm">{statusMessage || 'Please try again'}</p>
              </div>
            )}
          </div>

          {/* Phone Number Display */}
          {!showOutcomeModal && !showSettings && (
            <div className="px-5 pb-3">
              <div className="bg-slate-800/80 rounded-2xl p-4 flex items-center justify-between border border-slate-700/50">
                <input
                  type="tel"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value.replace(/[^\d+\-\s()]/g, ''))}
                  placeholder="Lead's phone number"
                  className="bg-transparent text-white text-2xl font-light w-full outline-none placeholder-slate-500 tracking-wide"
                  disabled={isCallActive}
                  data-testid="phone-input"
                />
                {phoneNumber && !isCallActive && (
                  <button
                    onClick={handleBackspace}
                    className="p-2 text-slate-400 hover:text-white hover:bg-slate-700 rounded-lg transition-all ml-2"
                  >
                    <Delete className="w-6 h-6" />
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Dial Pad */}
          {!isCallActive && !showOutcomeModal && !showSettings && (
            <div className="px-5 pb-3">
              <div className="grid grid-cols-3 gap-2">
                {dialPadButtons.flat().map((btn) => (
                  <button
                    key={btn.digit}
                    onClick={() => handleDigitPress(btn.digit)}
                    className="h-16 rounded-2xl bg-slate-800/60 hover:bg-slate-700/80 border border-slate-700/30 text-white transition-all active:scale-95 flex flex-col items-center justify-center"
                    data-testid={`dial-${btn.digit}`}
                  >
                    <span className="text-2xl font-light">{btn.digit}</span>
                    {btn.letters && <span className="text-[10px] text-slate-500 tracking-widest">{btn.letters}</span>}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Recording Toggle */}
          {!isCallActive && !showOutcomeModal && !showSettings && (
            <div className="px-5 pb-3">
              <button
                onClick={() => setIsRecording(!isRecording)}
                className={`w-full flex items-center justify-between p-3.5 rounded-2xl cursor-pointer transition-all border ${
                  isRecording 
                    ? 'bg-red-500/10 border-red-500/30' 
                    : 'bg-slate-800/60 border-slate-700/30'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Circle className={`w-5 h-5 ${isRecording ? 'fill-red-500 text-red-500' : 'text-slate-500'}`} />
                  <span className={`text-sm font-medium ${isRecording ? 'text-red-400' : 'text-slate-400'}`}>
                    Record this call
                  </span>
                </div>
                <div className={`w-11 h-6 rounded-full transition-colors ${isRecording ? 'bg-red-500' : 'bg-slate-600'}`}>
                  <div className={`w-5 h-5 bg-white rounded-full shadow-md transform transition-transform mt-0.5 ${isRecording ? 'translate-x-5 ml-0.5' : 'translate-x-0.5'}`} />
                </div>
              </button>
            </div>
          )}

          {/* Recent Calls */}
          {!isCallActive && !showOutcomeModal && !showSettings && recentCalls.length > 0 && (
            <div className="px-5 pb-3">
              <button
                onClick={() => setShowRecentCalls(!showRecentCalls)}
                className="w-full text-left text-sm text-slate-400 hover:text-white transition-colors flex items-center gap-2"
              >
                <Clock className="w-4 h-4" />
                Recent calls ({recentCalls.length})
              </button>
              {showRecentCalls && (
                <div className="mt-2 space-y-1 max-h-32 overflow-y-auto">
                  {recentCalls.map((call, idx) => (
                    <button
                      key={idx}
                      onClick={() => redialNumber(call.phone_number)}
                      className="w-full flex items-center justify-between p-2 rounded-lg bg-slate-800/50 hover:bg-slate-700/50 transition-colors"
                    >
                      <span className="text-white text-sm">{formatPhoneDisplay(call.phone_number)}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        call.outcome === 'connected' ? 'bg-green-500/20 text-green-400' :
                        call.outcome === 'no_answer' ? 'bg-yellow-500/20 text-yellow-400' :
                        'bg-slate-600 text-slate-400'
                      }`}>
                        {call.outcome?.replace('_', ' ')}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Call Button */}
          {!showOutcomeModal && !showSettings && (
            <div className="p-5 pt-2">
              {!isCallActive ? (
                <button
                  onClick={initiateCall}
                  disabled={!phoneNumber || phoneNumber.replace(/\D/g, '').length < 10 || !user?.phone}
                  className="w-full h-16 bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 disabled:from-slate-600 disabled:to-slate-700 disabled:cursor-not-allowed rounded-full flex items-center justify-center gap-3 text-white font-semibold text-lg transition-all active:scale-95 shadow-lg shadow-green-500/30 disabled:shadow-none"
                  data-testid="call-btn"
                >
                  <Phone className="w-6 h-6" />
                  {!user?.phone ? 'Set Your Phone First' : 'Call'}
                </button>
              ) : (
                <button
                  onClick={endCall}
                  className="w-full h-16 bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 rounded-full flex items-center justify-center gap-3 text-white font-semibold text-lg transition-all active:scale-95 shadow-lg shadow-red-500/30"
                  data-testid="end-call-btn"
                >
                  <PhoneOff className="w-6 h-6" />
                  End Call
                </button>
              )}
            </div>
          )}

          {/* Call Outcome Modal */}
          {showOutcomeModal && (
            <div className="p-5">
              <h3 className="text-white font-semibold text-lg mb-4 flex items-center gap-2">
                <FileText className="w-5 h-5 text-primary" />
                Log Call Outcome
              </h3>
              
              <div className="grid grid-cols-2 gap-2 mb-4">
                {callOutcomes.map((outcome) => (
                  <button
                    key={outcome.id}
                    onClick={() => setSelectedOutcome(outcome.id)}
                    className={`p-3 rounded-xl border-2 transition-all flex flex-col items-center gap-1 ${
                      selectedOutcome === outcome.id
                        ? 'border-primary bg-primary/10'
                        : 'border-slate-700 hover:border-slate-600 bg-slate-800/50'
                    }`}
                  >
                    <outcome.icon className={`w-5 h-5 ${outcome.color}`} />
                    <span className="text-white text-sm font-medium">{outcome.label}</span>
                  </button>
                ))}
              </div>

              <textarea
                value={callNotes}
                onChange={(e) => setCallNotes(e.target.value)}
                placeholder="Add notes..."
                className="w-full p-3 bg-slate-800/50 border border-slate-700 rounded-xl text-white text-sm placeholder-slate-500 resize-none mb-4"
                rows={2}
              />

              <div className="flex gap-3">
                <button
                  onClick={skipOutcomeLog}
                  className="flex-1 py-3 border border-slate-600 text-slate-400 rounded-xl hover:bg-slate-800 transition-colors"
                >
                  Skip
                </button>
                <button
                  onClick={saveCallOutcome}
                  disabled={!selectedOutcome || savingOutcome}
                  className="flex-1 py-3 bg-primary text-white rounded-xl hover:bg-primary/90 disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {savingOutcome ? <Loader2 className="w-5 h-5 animate-spin" /> : <Save className="w-5 h-5" />}
                  Save
                </button>
              </div>
            </div>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default PhoneDialer;
