import React, { useState, useRef, useEffect } from 'react';
import { 
  Video, VideoOff, Mic, MicOff, Monitor, MonitorOff, 
  Phone, PhoneOff, Users, MessageSquare, Settings,
  Maximize, Minimize, Copy, Check, X, Share2
} from 'lucide-react';
import { toast } from 'react-toastify';
import { motion, AnimatePresence } from 'framer-motion';

const VideoMeetingRoom = ({ meetingId, meetingTitle, onLeave, participants = [] }) => {
  const [isVideoOn, setIsVideoOn] = useState(true);
  const [isAudioOn, setIsAudioOn] = useState(true);
  const [isScreenSharing, setIsScreenSharing] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showChat, setShowChat] = useState(false);
  const [showParticipants, setShowParticipants] = useState(false);
  const [copied, setCopied] = useState(false);
  const [chatMessages, setChatMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [elapsedTime, setElapsedTime] = useState(0);
  
  const localVideoRef = useRef(null);
  const screenShareRef = useRef(null);
  const localStreamRef = useRef(null);
  const screenStreamRef = useRef(null);
  const containerRef = useRef(null);

  useEffect(() => {
    // Start local video
    startLocalVideo();
    
    // Timer for meeting duration
    const timer = setInterval(() => {
      setElapsedTime(prev => prev + 1);
    }, 1000);

    return () => {
      clearInterval(timer);
      stopAllStreams();
    };
  }, []);

  const startLocalVideo = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: true,
        audio: true
      });
      localStreamRef.current = stream;
      if (localVideoRef.current) {
        localVideoRef.current.srcObject = stream;
      }
    } catch (error) {
      console.error('Error accessing camera:', error);
      toast.error('Could not access camera/microphone');
    }
  };

  const stopAllStreams = () => {
    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach(track => track.stop());
    }
    if (screenStreamRef.current) {
      screenStreamRef.current.getTracks().forEach(track => track.stop());
    }
  };

  const toggleVideo = () => {
    if (localStreamRef.current) {
      const videoTrack = localStreamRef.current.getVideoTracks()[0];
      if (videoTrack) {
        videoTrack.enabled = !videoTrack.enabled;
        setIsVideoOn(videoTrack.enabled);
      }
    }
  };

  const toggleAudio = () => {
    if (localStreamRef.current) {
      const audioTrack = localStreamRef.current.getAudioTracks()[0];
      if (audioTrack) {
        audioTrack.enabled = !audioTrack.enabled;
        setIsAudioOn(audioTrack.enabled);
      }
    }
  };

  const toggleScreenShare = async () => {
    if (isScreenSharing) {
      // Stop screen sharing
      if (screenStreamRef.current) {
        screenStreamRef.current.getTracks().forEach(track => track.stop());
        screenStreamRef.current = null;
      }
      setIsScreenSharing(false);
      toast.info('Screen sharing stopped');
    } else {
      // Start screen sharing
      try {
        const stream = await navigator.mediaDevices.getDisplayMedia({
          video: {
            cursor: 'always',
            displaySurface: 'monitor'
          },
          audio: true
        });
        
        screenStreamRef.current = stream;
        if (screenShareRef.current) {
          screenShareRef.current.srcObject = stream;
        }
        
        // Listen for when user stops sharing via browser UI
        stream.getVideoTracks()[0].onended = () => {
          setIsScreenSharing(false);
          screenStreamRef.current = null;
          toast.info('Screen sharing stopped');
        };
        
        setIsScreenSharing(true);
        toast.success('Screen sharing started');
      } catch (error) {
        console.error('Error sharing screen:', error);
        if (error.name !== 'AbortError') {
          toast.error('Could not share screen');
        }
      }
    }
  };

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      containerRef.current?.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  const copyMeetingLink = () => {
    const link = `${window.location.origin}/meeting/${meetingId}`;
    navigator.clipboard.writeText(link);
    setCopied(true);
    toast.success('Meeting link copied!');
    setTimeout(() => setCopied(false), 2000);
  };

  const sendMessage = (e) => {
    e.preventDefault();
    if (!newMessage.trim()) return;
    
    setChatMessages(prev => [...prev, {
      id: Date.now(),
      sender: 'You',
      text: newMessage,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }]);
    setNewMessage('');
  };

  const leaveMeeting = () => {
    stopAllStreams();
    onLeave?.();
  };

  const formatTime = (seconds) => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    if (hrs > 0) {
      return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div 
      ref={containerRef}
      className="fixed inset-0 bg-slate-900 z-50 flex flex-col"
      data-testid="video-meeting-room"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 bg-slate-800/80 backdrop-blur-sm">
        <div className="flex items-center gap-4">
          <h2 className="text-white font-semibold text-lg">{meetingTitle || 'Video Meeting'}</h2>
          <span className="px-3 py-1 bg-red-500/20 text-red-400 rounded-full text-sm flex items-center gap-2">
            <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
            {formatTime(elapsedTime)}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={copyMeetingLink}
            className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-white rounded-lg text-sm flex items-center gap-2"
          >
            {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
            {copied ? 'Copied!' : 'Copy Link'}
          </button>
          <button
            onClick={toggleFullscreen}
            className="p-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg"
          >
            {isFullscreen ? <Minimize className="w-5 h-5" /> : <Maximize className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Video Grid */}
        <div className={`flex-1 p-4 ${showChat || showParticipants ? 'pr-0' : ''}`}>
          <div className={`h-full grid gap-4 ${isScreenSharing ? 'grid-cols-1' : 'grid-cols-2'}`}>
            {/* Screen Share (if active) */}
            {isScreenSharing && (
              <div className="relative bg-black rounded-2xl overflow-hidden shadow-2xl">
                <video
                  ref={screenShareRef}
                  autoPlay
                  playsInline
                  className="w-full h-full object-contain"
                />
                <div className="absolute top-4 left-4 px-3 py-1 bg-green-500 text-white rounded-full text-sm flex items-center gap-2">
                  <Monitor className="w-4 h-4" />
                  You are sharing your screen
                </div>
              </div>
            )}

            {/* Local Video */}
            <div className={`relative bg-slate-800 rounded-2xl overflow-hidden shadow-2xl ${isScreenSharing ? 'absolute bottom-20 right-8 w-64 h-48 z-10' : ''}`}>
              <video
                ref={localVideoRef}
                autoPlay
                playsInline
                muted
                className={`w-full h-full object-cover ${!isVideoOn ? 'hidden' : ''}`}
              />
              {!isVideoOn && (
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="w-24 h-24 bg-gradient-to-br from-primary to-blue-600 rounded-full flex items-center justify-center text-white text-3xl font-bold">
                    You
                  </div>
                </div>
              )}
              <div className="absolute bottom-4 left-4 px-3 py-1 bg-black/50 backdrop-blur-sm text-white rounded-full text-sm">
                You {!isAudioOn && '(Muted)'}
              </div>
            </div>

            {/* Participant placeholders */}
            {!isScreenSharing && participants.map((participant, idx) => (
              <div key={idx} className="relative bg-slate-800 rounded-2xl overflow-hidden shadow-2xl">
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="w-24 h-24 bg-gradient-to-br from-purple-500 to-pink-600 rounded-full flex items-center justify-center text-white text-3xl font-bold">
                    {participant.name?.charAt(0) || 'P'}
                  </div>
                </div>
                <div className="absolute bottom-4 left-4 px-3 py-1 bg-black/50 backdrop-blur-sm text-white rounded-full text-sm">
                  {participant.name || `Participant ${idx + 1}`}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Side Panel - Chat */}
        <AnimatePresence>
          {showChat && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 350, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              className="bg-slate-800 border-l border-slate-700 flex flex-col"
            >
              <div className="p-4 border-b border-slate-700 flex items-center justify-between">
                <h3 className="text-white font-semibold">Meeting Chat</h3>
                <button onClick={() => setShowChat(false)} className="text-slate-400 hover:text-white">
                  <X className="w-5 h-5" />
                </button>
              </div>
              <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {chatMessages.length === 0 ? (
                  <p className="text-slate-500 text-center text-sm">No messages yet</p>
                ) : (
                  chatMessages.map(msg => (
                    <div key={msg.id} className="bg-slate-700/50 rounded-lg p-3">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-white font-medium text-sm">{msg.sender}</span>
                        <span className="text-slate-500 text-xs">{msg.time}</span>
                      </div>
                      <p className="text-slate-300 text-sm">{msg.text}</p>
                    </div>
                  ))
                )}
              </div>
              <form onSubmit={sendMessage} className="p-4 border-t border-slate-700">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    placeholder="Type a message..."
                    className="flex-1 px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white text-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                  <button
                    type="submit"
                    className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90"
                  >
                    Send
                  </button>
                </div>
              </form>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Side Panel - Participants */}
        <AnimatePresence>
          {showParticipants && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 300, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              className="bg-slate-800 border-l border-slate-700 flex flex-col"
            >
              <div className="p-4 border-b border-slate-700 flex items-center justify-between">
                <h3 className="text-white font-semibold">Participants ({participants.length + 1})</h3>
                <button onClick={() => setShowParticipants(false)} className="text-slate-400 hover:text-white">
                  <X className="w-5 h-5" />
                </button>
              </div>
              <div className="flex-1 overflow-y-auto p-4 space-y-2">
                <div className="flex items-center gap-3 p-2 bg-slate-700/50 rounded-lg">
                  <div className="w-10 h-10 bg-gradient-to-br from-primary to-blue-600 rounded-full flex items-center justify-center text-white font-semibold">
                    You
                  </div>
                  <div>
                    <p className="text-white text-sm font-medium">You (Host)</p>
                    <p className="text-slate-400 text-xs">{isAudioOn ? 'Unmuted' : 'Muted'}</p>
                  </div>
                </div>
                {participants.map((p, idx) => (
                  <div key={idx} className="flex items-center gap-3 p-2 bg-slate-700/50 rounded-lg">
                    <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-pink-600 rounded-full flex items-center justify-center text-white font-semibold">
                      {p.name?.charAt(0) || 'P'}
                    </div>
                    <div>
                      <p className="text-white text-sm font-medium">{p.name || `Participant ${idx + 1}`}</p>
                      <p className="text-slate-400 text-xs">Connected</p>
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Controls */}
      <div className="px-6 py-4 bg-slate-800/80 backdrop-blur-sm">
        <div className="flex items-center justify-center gap-4">
          <button
            onClick={toggleAudio}
            className={`p-4 rounded-full transition-all ${
              isAudioOn 
                ? 'bg-slate-700 hover:bg-slate-600 text-white' 
                : 'bg-red-500 hover:bg-red-600 text-white'
            }`}
            title={isAudioOn ? 'Mute' : 'Unmute'}
          >
            {isAudioOn ? <Mic className="w-6 h-6" /> : <MicOff className="w-6 h-6" />}
          </button>

          <button
            onClick={toggleVideo}
            className={`p-4 rounded-full transition-all ${
              isVideoOn 
                ? 'bg-slate-700 hover:bg-slate-600 text-white' 
                : 'bg-red-500 hover:bg-red-600 text-white'
            }`}
            title={isVideoOn ? 'Turn off camera' : 'Turn on camera'}
          >
            {isVideoOn ? <Video className="w-6 h-6" /> : <VideoOff className="w-6 h-6" />}
          </button>

          <button
            onClick={toggleScreenShare}
            className={`p-4 rounded-full transition-all ${
              isScreenSharing 
                ? 'bg-green-500 hover:bg-green-600 text-white' 
                : 'bg-slate-700 hover:bg-slate-600 text-white'
            }`}
            title={isScreenSharing ? 'Stop sharing' : 'Share screen'}
            data-testid="screen-share-btn"
          >
            {isScreenSharing ? <MonitorOff className="w-6 h-6" /> : <Monitor className="w-6 h-6" />}
          </button>

          <div className="w-px h-10 bg-slate-600 mx-2" />

          <button
            onClick={() => { setShowChat(!showChat); setShowParticipants(false); }}
            className={`p-4 rounded-full transition-all ${
              showChat 
                ? 'bg-primary text-white' 
                : 'bg-slate-700 hover:bg-slate-600 text-white'
            }`}
            title="Chat"
          >
            <MessageSquare className="w-6 h-6" />
          </button>

          <button
            onClick={() => { setShowParticipants(!showParticipants); setShowChat(false); }}
            className={`p-4 rounded-full transition-all ${
              showParticipants 
                ? 'bg-primary text-white' 
                : 'bg-slate-700 hover:bg-slate-600 text-white'
            }`}
            title="Participants"
          >
            <Users className="w-6 h-6" />
          </button>

          <div className="w-px h-10 bg-slate-600 mx-2" />

          <button
            onClick={leaveMeeting}
            className="px-6 py-4 bg-red-500 hover:bg-red-600 text-white rounded-full flex items-center gap-2 font-medium"
            title="Leave meeting"
          >
            <PhoneOff className="w-6 h-6" />
            Leave
          </button>
        </div>
      </div>
    </div>
  );
};

export default VideoMeetingRoom;
