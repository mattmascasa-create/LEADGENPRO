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
import CallDispositionModal from './CallDispositionModal';

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
          className="bg-gradient-to-b from-slate-900 via-slate-800 to-slate-900 rounded-3xl shadow-2xl w-full max-w-xl overflow-hidden border border-slate-700/50"
          data-testid="phone-dialer"
        >
          {/* Header */}
          <div className="p-6 text-center relative">
            {!isCallActive && !showOutcomeModal && (
              <div className="absolute right-5 top-5 flex gap-2">
                <button
                  onClick={() => setShowSettings(!showSettings)}
                  className={`p-2.5 rounded-full transition-all ${showSettings ? 'bg-primary text-white' : 'text-slate-400 hover:text-white hover:bg-slate-700/50'}`}
                  title="Settings"
                >
                  <Settings className="w-5 h-5" />
                </button>
                <button
                  onClick={onClose}
                  className="p-2.5 text-slate-400 hover:text-white hover:bg-slate-700/50 rounded-full transition-all"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            )}
            
            {/* Lead Info */}
            {leadInfo && !showSettings && (
              <div className="mb-6">
                <div className="w-20 h-20 bg-gradient-to-br from-primary to-blue-600 rounded-full flex items-center justify-center mx-auto mb-3 shadow-lg shadow-primary/30">
                  <User className="w-10 h-10 text-white" />
                </div>
                <p className="text-white font-semibold text-xl">{leadInfo.first_name} {leadInfo.last_name}</p>
                <p className="text-slate-400">{leadInfo.company}</p>
              </div>
            )}

            {!leadInfo && !isCallActive && !showSettings && (
              <div className="mb-4">
                <div className="w-18 h-18 bg-gradient-to-br from-green-500 to-emerald-600 rounded-full flex items-center justify-center mx-auto mb-3 shadow-lg shadow-green-500/30" style={{width: '72px', height: '72px'}}>
                  <Phone className="w-9 h-9 text-white" />
                </div>
                <h2 className="text-white font-semibold text-xl">Click-to-Call Dialer</h2>
                <p className="text-slate-500 text-sm mt-1">We'll call your phone first, then connect you to the lead</p>
              </div>
            )}

            {/* Settings Panel - Now Larger */}
            {showSettings && !isCallActive && (
              <div className="text-left mt-8 max-w-md mx-auto">
                <h3 className="text-white font-semibold text-lg mb-4 flex items-center gap-2">
                  <Settings className="w-5 h-5 text-primary" />
                  Your Phone Number
                </h3>
                <div className="bg-slate-800/50 rounded-xl p-5 border border-slate-700/50 mb-4">
                  <div className="flex items-start gap-3 mb-4">
                    <Info className="w-5 h-5 text-blue-400 mt-0.5 flex-shrink-0" />
                    <p className="text-slate-400 text-sm">
                      When you make a call, we'll ring your phone first. Answer and press 1 to connect to the lead.
                    </p>
                  </div>
                  <input
                    type="tel"
                    value={agentPhone}
                    onChange={(e) => setAgentPhone(e.target.value.replace(/[^\d+\-\s()]/g, ''))}
                    placeholder="Your phone number (e.g., +1 555 123 4567)"
                    className="w-full px-4 py-4 bg-slate-700/50 border border-slate-600 rounded-xl text-white text-lg placeholder-slate-500 mb-4"
                  />
                  <button
                    onClick={saveAgentPhone}
                    disabled={savingPhone}
                    className="w-full py-4 bg-primary text-white rounded-xl font-medium text-lg hover:bg-primary/90 disabled:opacity-50 flex items-center justify-center gap-2"
                  >
                    {savingPhone ? <Loader2 className="w-5 h-5 animate-spin" /> : <Save className="w-5 h-5" />}
                    Save Phone Number
                  </button>
                </div>
                {user?.phone && (
                  <p className="text-green-400 text-center">
                    ✓ Your phone: {formatPhoneDisplay(user.phone)}
                  </p>
                )}
              </div>
            )}

            {/* Call Status Display */}
            {callStatus === 'calling_agent' && (
              <div className="py-6">
                <motion.div
                  animate={{ scale: [1, 1.1, 1] }}
                  transition={{ repeat: Infinity, duration: 1.5 }}
                  className="w-24 h-24 bg-blue-500/20 rounded-full flex items-center justify-center mx-auto mb-4"
                >
                  <PhoneIncoming className="w-12 h-12 text-blue-400" />
                </motion.div>
                <p className="text-blue-400 font-semibold text-xl">Calling Your Phone...</p>
                <p className="text-slate-500 mt-2">{statusMessage}</p>
                <p className="text-slate-400 text-sm mt-3 bg-slate-800/50 py-2 px-4 rounded-full inline-block">Answer and press 1 to connect</p>
              </div>
            )}

            {callStatus === 'connecting' && (
              <div className="py-6">
                <motion.div
                  animate={{ scale: [1, 1.1, 1] }}
                  transition={{ repeat: Infinity, duration: 1.5 }}
                  className="w-24 h-24 bg-yellow-500/20 rounded-full flex items-center justify-center mx-auto mb-4"
                >
                  <PhoneCall className="w-12 h-12 text-yellow-400" />
                </motion.div>
                <p className="text-yellow-400 font-semibold text-xl">Connecting to Lead...</p>
                <p className="text-slate-400 mt-1">{formatPhoneDisplay(phoneNumber)}</p>
                <div className="flex items-center justify-center gap-3 mt-4 text-white text-3xl font-mono">
                  <Clock className="w-6 h-6 text-slate-400" />
                  {formatDuration(callDuration)}
                </div>
              </div>
            )}

            {callStatus === 'connected' && (
              <div className="py-6">
                <div className="flex items-center justify-center gap-3 mb-4">
                  <motion.div
                    animate={{ scale: [1, 1.2, 1] }}
                    transition={{ repeat: Infinity, duration: 1 }}
                  >
                    <Circle className="w-4 h-4 text-green-500 fill-green-500" />
                  </motion.div>
                  <span className="text-green-400 font-semibold text-xl">Connected</span>
                </div>
                <div className="flex items-center justify-center gap-2 text-white text-6xl font-mono mb-3">
                  {formatDuration(callDuration)}
                </div>
                <p className="text-slate-400">{formatPhoneDisplay(phoneNumber)}</p>
                {isRecording && (
                  <div className="flex items-center justify-center gap-2 mt-4 text-red-400">
                    <Circle className="w-3 h-3 fill-red-500 animate-pulse" />
                    <span className="font-medium">Recording in progress</span>
                  </div>
                )}
              </div>
            )}

            {callStatus === 'ended' && !showOutcomeModal && (
              <div className="py-6">
                <div className="w-20 h-20 bg-slate-700 rounded-full flex items-center justify-center mx-auto mb-4">
                  <PhoneOff className="w-10 h-10 text-slate-400" />
                </div>
                <p className="text-slate-300 font-semibold text-xl">Call Ended</p>
                <p className="text-slate-500 mt-1">Duration: {formatDuration(callDuration)}</p>
              </div>
            )}

            {callStatus === 'failed' && (
              <div className="py-6">
                <div className="w-20 h-20 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                  <AlertCircle className="w-10 h-10 text-red-400" />
                </div>
                <p className="text-red-400 font-semibold text-xl">Call Failed</p>
                <p className="text-slate-500 mt-1">{statusMessage || 'Please try again'}</p>
              </div>
            )}
          </div>

          {/* Phone Number Display - Larger */}
          {!showOutcomeModal && !showSettings && (
            <div className="px-6 pb-4">
              <div className="bg-slate-800/80 rounded-2xl p-5 flex items-center justify-between border border-slate-700/50">
                <input
                  type="tel"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value.replace(/[^\d+\-\s()]/g, ''))}
                  placeholder="Enter phone number"
                  className="bg-transparent text-white text-3xl font-light w-full outline-none placeholder-slate-500 tracking-wide"
                  disabled={isCallActive}
                  data-testid="phone-input"
                />
                {phoneNumber && !isCallActive && (
                  <button
                    onClick={handleBackspace}
                    className="p-3 text-slate-400 hover:text-white hover:bg-slate-700 rounded-lg transition-all ml-2"
                  >
                    <Delete className="w-7 h-7" />
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Dial Pad - Larger */}
          {!isCallActive && !showOutcomeModal && !showSettings && (
            <div className="px-6 pb-4">
              <div className="grid grid-cols-3 gap-3 max-w-sm mx-auto">
                {dialPadButtons.flat().map((btn) => (
                  <button
                    key={btn.digit}
                    onClick={() => handleDigitPress(btn.digit)}
                    className="h-18 rounded-2xl bg-slate-800/60 hover:bg-slate-700/80 border border-slate-700/30 text-white transition-all active:scale-95 flex flex-col items-center justify-center"
                    style={{height: '72px'}}
                    data-testid={`dial-${btn.digit}`}
                  >
                    <span className="text-3xl font-light">{btn.digit}</span>
                    {btn.letters && <span className="text-xs text-slate-500 tracking-widest">{btn.letters}</span>}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Recording Toggle */}
          {!isCallActive && !showOutcomeModal && !showSettings && (
            <div className="px-6 pb-4">
              <button
                onClick={() => setIsRecording(!isRecording)}
                className={`w-full flex items-center justify-between p-4 rounded-2xl cursor-pointer transition-all border ${
                  isRecording 
                    ? 'bg-red-500/10 border-red-500/30' 
                    : 'bg-slate-800/60 border-slate-700/30'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Circle className={`w-6 h-6 ${isRecording ? 'fill-red-500 text-red-500' : 'text-slate-500'}`} />
                  <span className={`font-medium ${isRecording ? 'text-red-400' : 'text-slate-400'}`}>
                    Record this call
                  </span>
                </div>
                <div className={`w-12 h-7 rounded-full transition-colors ${isRecording ? 'bg-red-500' : 'bg-slate-600'}`}>
                  <div className={`w-6 h-6 bg-white rounded-full shadow-md transform transition-transform mt-0.5 ${isRecording ? 'translate-x-5 ml-0.5' : 'translate-x-0.5'}`} />
                </div>
              </button>
            </div>
          )}

          {/* Recent Calls */}
          {!isCallActive && !showOutcomeModal && !showSettings && recentCalls.length > 0 && (
            <div className="px-6 pb-4">
              <button
                onClick={() => setShowRecentCalls(!showRecentCalls)}
                className="w-full text-left text-slate-400 hover:text-white transition-colors flex items-center gap-2"
              >
                <Clock className="w-5 h-5" />
                Recent calls ({recentCalls.length})
              </button>
              {showRecentCalls && (
                <div className="mt-3 space-y-2 max-h-40 overflow-y-auto">
                  {recentCalls.map((call, idx) => (
                    <button
                      key={idx}
                      onClick={() => redialNumber(call.phone_number)}
                      className="w-full flex items-center justify-between p-3 rounded-xl bg-slate-800/50 hover:bg-slate-700/50 transition-colors"
                    >
                      <span className="text-white">{formatPhoneDisplay(call.phone_number)}</span>
                      <span className={`text-xs px-2 py-1 rounded-full ${
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
        </motion.div>
      </motion.div>

      {/* Call Disposition Modal - Separate overlay */}
      <CallDispositionModal
        isOpen={showOutcomeModal}
        onClose={skipOutcomeLog}
        callId={callId}
        leadInfo={leadInfo}
        callDuration={callDuration}
        onDispositionSaved={() => {
          setShowOutcomeModal(false);
          resetDialer();
          fetchRecentCalls();
        }}
      />
    </AnimatePresence>
  );
};

export default PhoneDialer;
