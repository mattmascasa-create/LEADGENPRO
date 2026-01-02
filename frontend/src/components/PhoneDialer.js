import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { 
  Phone, PhoneOff, Mic, MicOff, Volume2, VolumeX, 
  Delete, X, Loader2, Clock, User, Circle
} from 'lucide-react';
import { toast } from 'react-toastify';
import { motion, AnimatePresence } from 'framer-motion';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const PhoneDialer = ({ isOpen, onClose, prefilledNumber = '', leadInfo = null }) => {
  const [phoneNumber, setPhoneNumber] = useState(prefilledNumber);
  const [isCallActive, setIsCallActive] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [isSpeakerOn, setIsSpeakerOn] = useState(true);
  const [isRecording, setIsRecording] = useState(true);
  const [callDuration, setCallDuration] = useState(0);
  const [callStatus, setCallStatus] = useState('idle'); // idle, connecting, connected, ended
  const [callSid, setCallSid] = useState(null);
  const timerRef = useRef(null);

  useEffect(() => {
    if (prefilledNumber) {
      setPhoneNumber(prefilledNumber);
    }
  }, [prefilledNumber]);

  useEffect(() => {
    if (callStatus === 'connected') {
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

  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const dialPadButtons = [
    ['1', '2', '3'],
    ['4', '5', '6'],
    ['7', '8', '9'],
    ['*', '0', '#']
  ];

  const handleDigitPress = (digit) => {
    if (phoneNumber.length < 15) {
      setPhoneNumber(prev => prev + digit);
    }
  };

  const handleBackspace = () => {
    setPhoneNumber(prev => prev.slice(0, -1));
  };

  const handleClear = () => {
    setPhoneNumber('');
  };

  const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return { headers: { Authorization: `Bearer ${token}` } };
  };

  const initiateCall = async () => {
    if (!phoneNumber || phoneNumber.length < 10) {
      toast.error('Please enter a valid phone number');
      return;
    }

    // Format phone number
    let formattedNumber = phoneNumber.replace(/\D/g, '');
    if (!formattedNumber.startsWith('+')) {
      if (formattedNumber.startsWith('1') && formattedNumber.length === 11) {
        formattedNumber = '+' + formattedNumber;
      } else if (formattedNumber.length === 10) {
        formattedNumber = '+1' + formattedNumber;
      } else {
        formattedNumber = '+' + formattedNumber;
      }
    }

    setCallStatus('connecting');
    setIsCallActive(true);
    setCallDuration(0);

    try {
      const response = await axios.post(
        `${API_URL}/api/voice/call`,
        {
          to_number: formattedNumber,
          lead_id: leadInfo?.id || null,
          record: isRecording
        },
        getAuthHeaders()
      );

      if (response.data.call_sid) {
        setCallSid(response.data.call_sid);
        setCallStatus('connected');
        toast.success('Call connected!');
        
        // Log the call
        if (leadInfo?.id) {
          await axios.post(
            `${API_URL}/api/calls/log`,
            {
              lead_id: leadInfo.id,
              phone_number: formattedNumber,
              outcome: 'connected',
              duration: 0,
              call_sid: response.data.call_sid
            },
            getAuthHeaders()
          );
        }
      }
    } catch (error) {
      console.error('Call error:', error);
      toast.error(error.response?.data?.detail || 'Failed to initiate call');
      setCallStatus('idle');
      setIsCallActive(false);
    }
  };

  const endCall = async () => {
    if (callSid) {
      try {
        await axios.post(
          `${API_URL}/api/voice/hangup`,
          { call_sid: callSid },
          getAuthHeaders()
        );
        
        // Update call log with duration
        if (leadInfo?.id) {
          await axios.post(
            `${API_URL}/api/calls/log`,
            {
              lead_id: leadInfo.id,
              phone_number: phoneNumber,
              outcome: 'connected',
              duration: callDuration,
              call_sid: callSid
            },
            getAuthHeaders()
          );
        }
      } catch (error) {
        console.error('Hangup error:', error);
      }
    }

    setCallStatus('ended');
    setTimeout(() => {
      setCallStatus('idle');
      setIsCallActive(false);
      setCallSid(null);
      setCallDuration(0);
    }, 1500);
  };

  const toggleMute = () => {
    setIsMuted(!isMuted);
    toast.info(isMuted ? 'Unmuted' : 'Muted');
  };

  const toggleSpeaker = () => {
    setIsSpeakerOn(!isSpeakerOn);
    toast.info(isSpeakerOn ? 'Speaker off' : 'Speaker on');
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4"
        onClick={(e) => e.target === e.currentTarget && !isCallActive && onClose()}
      >
        <motion.div
          initial={{ scale: 0.9, y: 20 }}
          animate={{ scale: 1, y: 0 }}
          exit={{ scale: 0.9, y: 20 }}
          className="bg-gradient-to-b from-slate-900 to-slate-800 rounded-3xl shadow-2xl w-full max-w-sm overflow-hidden"
          data-testid="phone-dialer"
        >
          {/* Header */}
          <div className="p-6 text-center relative">
            {!isCallActive && (
              <button
                onClick={onClose}
                className="absolute right-4 top-4 p-2 text-slate-400 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            )}
            
            {leadInfo && (
              <div className="mb-4">
                <div className="w-16 h-16 bg-gradient-to-br from-primary to-blue-600 rounded-full flex items-center justify-center mx-auto mb-2">
                  <User className="w-8 h-8 text-white" />
                </div>
                <p className="text-white font-medium">{leadInfo.first_name} {leadInfo.last_name}</p>
                <p className="text-slate-400 text-sm">{leadInfo.company}</p>
              </div>
            )}

            {/* Call Status */}
            {callStatus === 'connecting' && (
              <div className="text-center py-4">
                <Loader2 className="w-8 h-8 text-primary animate-spin mx-auto mb-2" />
                <p className="text-slate-300">Connecting...</p>
              </div>
            )}

            {callStatus === 'connected' && (
              <div className="text-center py-4">
                <div className="flex items-center justify-center gap-2 mb-2">
                  <Circle className="w-3 h-3 text-green-500 fill-green-500 animate-pulse" />
                  <span className="text-green-500 font-medium">Connected</span>
                </div>
                <div className="flex items-center justify-center gap-2 text-white text-3xl font-mono">
                  <Clock className="w-6 h-6 text-slate-400" />
                  {formatDuration(callDuration)}
                </div>
                {isRecording && (
                  <div className="flex items-center justify-center gap-1 mt-2 text-red-400 text-sm">
                    <Circle className="w-2 h-2 fill-red-500 animate-pulse" />
                    Recording
                  </div>
                )}
              </div>
            )}

            {callStatus === 'ended' && (
              <div className="text-center py-4">
                <p className="text-slate-300">Call Ended</p>
                <p className="text-slate-500 text-sm">Duration: {formatDuration(callDuration)}</p>
              </div>
            )}
          </div>

          {/* Phone Number Display */}
          <div className="px-6 pb-4">
            <div className="bg-slate-800/50 rounded-xl p-4 flex items-center justify-between">
              <input
                type="text"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value.replace(/[^\d+\-\s()]/g, ''))}
                placeholder="Enter phone number"
                className="bg-transparent text-white text-2xl font-light w-full outline-none placeholder-slate-500"
                disabled={isCallActive}
                data-testid="phone-input"
              />
              {phoneNumber && !isCallActive && (
                <button
                  onClick={handleBackspace}
                  className="p-2 text-slate-400 hover:text-white transition-colors"
                >
                  <Delete className="w-6 h-6" />
                </button>
              )}
            </div>
          </div>

          {/* Dial Pad */}
          {!isCallActive && (
            <div className="px-6 pb-4">
              <div className="grid grid-cols-3 gap-3">
                {dialPadButtons.flat().map((digit) => (
                  <button
                    key={digit}
                    onClick={() => handleDigitPress(digit)}
                    className="h-16 rounded-xl bg-slate-700/50 hover:bg-slate-600/50 text-white text-2xl font-light transition-all active:scale-95"
                    data-testid={`dial-${digit}`}
                  >
                    {digit}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* In-Call Controls */}
          {isCallActive && callStatus === 'connected' && (
            <div className="px-6 pb-4">
              <div className="grid grid-cols-3 gap-4">
                <button
                  onClick={toggleMute}
                  className={`h-16 rounded-xl flex flex-col items-center justify-center gap-1 transition-all ${
                    isMuted ? 'bg-red-500/20 text-red-400' : 'bg-slate-700/50 text-slate-300 hover:bg-slate-600/50'
                  }`}
                >
                  {isMuted ? <MicOff className="w-6 h-6" /> : <Mic className="w-6 h-6" />}
                  <span className="text-xs">{isMuted ? 'Unmute' : 'Mute'}</span>
                </button>
                <button
                  onClick={toggleSpeaker}
                  className={`h-16 rounded-xl flex flex-col items-center justify-center gap-1 transition-all ${
                    !isSpeakerOn ? 'bg-slate-700/50 text-slate-500' : 'bg-slate-700/50 text-slate-300 hover:bg-slate-600/50'
                  }`}
                >
                  {isSpeakerOn ? <Volume2 className="w-6 h-6" /> : <VolumeX className="w-6 h-6" />}
                  <span className="text-xs">Speaker</span>
                </button>
                <button
                  onClick={() => setIsRecording(!isRecording)}
                  className={`h-16 rounded-xl flex flex-col items-center justify-center gap-1 transition-all ${
                    isRecording ? 'bg-red-500/20 text-red-400' : 'bg-slate-700/50 text-slate-300 hover:bg-slate-600/50'
                  }`}
                >
                  <Circle className={`w-6 h-6 ${isRecording ? 'fill-red-500' : ''}`} />
                  <span className="text-xs">{isRecording ? 'Recording' : 'Record'}</span>
                </button>
              </div>
            </div>
          )}

          {/* Recording Toggle (before call) */}
          {!isCallActive && (
            <div className="px-6 pb-4">
              <label className="flex items-center justify-between p-3 bg-slate-800/50 rounded-xl cursor-pointer">
                <span className="text-slate-300 text-sm">Record this call</span>
                <div
                  onClick={() => setIsRecording(!isRecording)}
                  className={`w-12 h-6 rounded-full transition-colors ${isRecording ? 'bg-red-500' : 'bg-slate-600'}`}
                >
                  <div className={`w-5 h-5 bg-white rounded-full shadow-md transform transition-transform mt-0.5 ${isRecording ? 'translate-x-6 ml-0.5' : 'translate-x-0.5'}`} />
                </div>
              </label>
            </div>
          )}

          {/* Call Button */}
          <div className="p-6 pt-2">
            {!isCallActive ? (
              <button
                onClick={initiateCall}
                disabled={!phoneNumber || phoneNumber.length < 10}
                className="w-full h-16 bg-green-500 hover:bg-green-600 disabled:bg-slate-600 disabled:cursor-not-allowed rounded-full flex items-center justify-center gap-3 text-white font-medium text-lg transition-all active:scale-95"
                data-testid="call-btn"
              >
                <Phone className="w-6 h-6" />
                Call
              </button>
            ) : (
              <button
                onClick={endCall}
                className="w-full h-16 bg-red-500 hover:bg-red-600 rounded-full flex items-center justify-center gap-3 text-white font-medium text-lg transition-all active:scale-95"
                data-testid="end-call-btn"
              >
                <PhoneOff className="w-6 h-6" />
                End Call
              </button>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default PhoneDialer;
