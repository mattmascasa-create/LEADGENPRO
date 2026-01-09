import React, { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Play, Pause, SkipBack, SkipForward, Volume2, VolumeX,
  Loader2, Lightbulb, AlertTriangle, ThumbsUp, MessageSquare,
  Zap, Target, Clock, ChevronDown, ChevronUp, User, Users
} from 'lucide-react';

const WaveformPlayer = ({ 
  audioUrl, 
  duration = 0,
  coaching = null,
  transcript = null,
  onTimeUpdate = () => {}
}) => {
  const audioRef = useRef(null);
  const canvasRef = useRef(null);
  const progressRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [audioDuration, setAudioDuration] = useState(duration || 0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [waveformData, setWaveformData] = useState([]);
  const [activeInsight, setActiveInsight] = useState(null);
  const [showInsights, setShowInsights] = useState(true);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [isAnalyzingAudio, setIsAnalyzingAudio] = useState(false);
  const [audioAnalyzed, setAudioAnalyzed] = useState(false);

  // Analyze audio with Web Audio API to get real waveform data
  const analyzeAudioWaveform = useCallback(async () => {
    if (!audioUrl || audioAnalyzed || isAnalyzingAudio) return;
    
    setIsAnalyzingAudio(true);
    
    try {
      // Create audio context
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      const audioContext = new AudioContext();
      audioContextRef.current = audioContext;
      
      // Fetch the audio file
      const response = await fetch(audioUrl);
      const arrayBuffer = await response.arrayBuffer();
      
      // Decode the audio data
      const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
      
      // Get the raw audio data (use first channel)
      const rawData = audioBuffer.getChannelData(0);
      const samples = 150; // Number of bars in waveform
      const blockSize = Math.floor(rawData.length / samples);
      const waveform = [];
      
      for (let i = 0; i < samples; i++) {
        let sum = 0;
        const start = i * blockSize;
        
        // Calculate RMS (root mean square) for this block
        for (let j = 0; j < blockSize; j++) {
          sum += rawData[start + j] * rawData[start + j];
        }
        
        const rms = Math.sqrt(sum / blockSize);
        // Normalize and add some minimum height
        const normalizedHeight = Math.min(1, rms * 3) * 0.9 + 0.1;
        
        // Detect if this segment is likely speech vs silence
        const isSpeech = rms > 0.02;
        
        waveform.push({
          height: normalizedHeight,
          isSpeech,
          // Estimate speaker based on amplitude patterns (simplified)
          speaker: rms > 0.05 ? 'rep' : rms > 0.02 ? 'customer' : 'silence'
        });
      }
      
      setWaveformData(waveform);
      setAudioAnalyzed(true);
      setAudioDuration(audioBuffer.duration);
      
      // Close the context to free resources
      await audioContext.close();
      
    } catch (error) {
      console.error('Error analyzing audio:', error);
      // Fall back to generated waveform
      generateFallbackWaveform();
    } finally {
      setIsAnalyzingAudio(false);
    }
  }, [audioUrl, audioAnalyzed, isAnalyzingAudio]);

  // Fallback waveform generation
  const generateFallbackWaveform = () => {
    const bars = 150;
    const data = [];
    for (let i = 0; i < bars; i++) {
      const base = Math.sin(i * 0.1) * 0.3;
      const noise = Math.random() * 0.5;
      const speech = Math.sin(i * 0.05) * 0.2;
      data.push({
        height: Math.abs(base + noise + speech) * 0.8 + 0.1,
        isSpeech: Math.random() > 0.2,
        speaker: Math.random() > 0.5 ? 'rep' : 'customer'
      });
    }
    setWaveformData(data);
  };

  // Analyze audio when URL changes
  useEffect(() => {
    if (audioUrl) {
      setAudioAnalyzed(false);
      analyzeAudioWaveform();
    } else {
      generateFallbackWaveform();
    }
  }, [audioUrl]);

  // Parse coaching insights to get timestamped markers
  const getInsightMarkers = useCallback(() => {
    if (!coaching) return [];
    
    const markers = [];
    const totalDuration = audioDuration || 60;
    
    // Real-time suggestions with approximate timestamps
    if (coaching.real_time_suggestions) {
      coaching.real_time_suggestions.forEach((suggestion, i) => {
        // Distribute insights across the call timeline
        const time = (i + 1) * (totalDuration / (coaching.real_time_suggestions.length + 1));
        markers.push({
          time,
          type: 'suggestion',
          icon: Lightbulb,
          color: 'yellow',
          title: suggestion.skill || 'Coaching Moment',
          content: suggestion.suggestion,
          moment: suggestion.moment
        });
      });
    }

    // Sentiment shifts
    if (coaching.sentiment_analysis?.sentiment_shifts) {
      coaching.sentiment_analysis.sentiment_shifts.forEach((shift, i) => {
        const time = totalDuration * (0.3 + i * 0.2);
        markers.push({
          time,
          type: 'sentiment',
          icon: shift.shift.includes('positive') ? ThumbsUp : AlertTriangle,
          color: shift.shift.includes('positive') ? 'green' : 'orange',
          title: 'Sentiment Shift',
          content: shift.cause,
          moment: shift.moment
        });
      });
    }

    // Key moments - buying signals
    if (coaching.key_moments?.buying_signals) {
      coaching.key_moments.buying_signals.forEach((signal, i) => {
        const time = totalDuration * (0.4 + i * 0.15);
        markers.push({
          time,
          type: 'buying_signal',
          icon: Target,
          color: 'green',
          title: 'Buying Signal',
          content: signal.quote,
          moment: signal.signal_type
        });
      });
    }

    // Key moments - objections
    if (coaching.key_moments?.objections) {
      coaching.key_moments.objections.forEach((objection, i) => {
        const time = totalDuration * (0.5 + i * 0.1);
        markers.push({
          time,
          type: 'objection',
          icon: AlertTriangle,
          color: 'red',
          title: 'Objection',
          content: objection.quote,
          moment: `Handled: ${objection.how_handled}`,
          suggestion: objection.better_response
        });
      });
    }

    return markers.sort((a, b) => a.time - b.time);
  }, [coaching, audioDuration]);

  const insightMarkers = getInsightMarkers();

  // Handle audio events
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleLoadedMetadata = () => {
      setAudioDuration(audio.duration);
      setIsLoading(false);
    };

    const handleTimeUpdate = () => {
      setCurrentTime(audio.currentTime);
      onTimeUpdate(audio.currentTime);
      
      // Check if we're near an insight marker
      const nearbyInsight = insightMarkers.find(
        marker => Math.abs(marker.time - audio.currentTime) < 2
      );
      if (nearbyInsight && nearbyInsight !== activeInsight) {
        setActiveInsight(nearbyInsight);
      }
    };

    const handleEnded = () => {
      setIsPlaying(false);
      setActiveInsight(null);
    };

    const handleCanPlay = () => {
      setIsLoading(false);
    };

    audio.addEventListener('loadedmetadata', handleLoadedMetadata);
    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('canplay', handleCanPlay);

    return () => {
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('ended', handleEnded);
      audio.removeEventListener('canplay', handleCanPlay);
    };
  }, [insightMarkers, activeInsight, onTimeUpdate]);

  // Play/Pause toggle
  const togglePlay = () => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause();
      } else {
        audioRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  // Seek to position
  const handleSeek = (e) => {
    const rect = progressRef.current.getBoundingClientRect();
    const percent = (e.clientX - rect.left) / rect.width;
    const time = percent * audioDuration;
    if (audioRef.current) {
      audioRef.current.currentTime = time;
      setCurrentTime(time);
    }
  };

  // Skip forward/backward
  const skip = (seconds) => {
    if (audioRef.current) {
      audioRef.current.currentTime = Math.max(0, Math.min(audioDuration, audioRef.current.currentTime + seconds));
    }
  };

  // Jump to insight marker
  const jumpToInsight = (marker) => {
    if (audioRef.current) {
      audioRef.current.currentTime = Math.max(0, marker.time - 1);
      setCurrentTime(marker.time - 1);
      setActiveInsight(marker);
      if (!isPlaying) {
        audioRef.current.play();
        setIsPlaying(true);
      }
    }
  };

  // Toggle mute
  const toggleMute = () => {
    if (audioRef.current) {
      audioRef.current.muted = !isMuted;
      setIsMuted(!isMuted);
    }
  };

  // Change playback rate
  const changePlaybackRate = () => {
    const rates = [1, 1.25, 1.5, 1.75, 2];
    const currentIndex = rates.indexOf(playbackRate);
    const nextRate = rates[(currentIndex + 1) % rates.length];
    setPlaybackRate(nextRate);
    if (audioRef.current) {
      audioRef.current.playbackRate = nextRate;
    }
  };

  // Format time
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const progress = audioDuration > 0 ? (currentTime / audioDuration) * 100 : 0;

  return (
    <div className="bg-gradient-to-br from-slate-900 to-slate-800 rounded-xl p-5 space-y-4">
      {/* Hidden audio element */}
      <audio ref={audioRef} src={audioUrl} preload="metadata" />

      {/* Header */}
      <div className="flex items-center justify-between">
        <h4 className="text-white font-semibold flex items-center gap-2">
          <div className="w-8 h-8 bg-primary/20 rounded-lg flex items-center justify-center">
            <Volume2 className="w-4 h-4 text-primary" />
          </div>
          Call Recording
        </h4>
        {coaching && (
          <button
            onClick={() => setShowInsights(!showInsights)}
            className="flex items-center gap-2 px-3 py-1.5 bg-yellow-500/20 text-yellow-400 rounded-lg text-sm hover:bg-yellow-500/30 transition-colors"
          >
            <Lightbulb className="w-4 h-4" />
            {showInsights ? 'Hide' : 'Show'} AI Insights
            {showInsights ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>
        )}
      </div>

      {/* Waveform Visualization */}
      <div 
        ref={progressRef}
        className="relative h-24 bg-slate-800/50 rounded-lg cursor-pointer overflow-hidden"
        onClick={handleSeek}
      >
        {/* Waveform bars */}
        <div className="absolute inset-0 flex items-center justify-around px-2">
          {waveformData.map((height, i) => {
            const barProgress = (i / waveformData.length) * 100;
            const isPast = barProgress <= progress;
            return (
              <div
                key={i}
                className={`w-1 rounded-full transition-all duration-75 ${
                  isPast ? 'bg-primary' : 'bg-slate-600'
                }`}
                style={{ 
                  height: `${height * 80}%`,
                  opacity: isPast ? 1 : 0.5
                }}
              />
            );
          })}
        </div>

        {/* Progress overlay */}
        <div 
          className="absolute top-0 left-0 h-full bg-primary/10 pointer-events-none"
          style={{ width: `${progress}%` }}
        />

        {/* Playhead */}
        <div 
          className="absolute top-0 h-full w-0.5 bg-primary shadow-lg shadow-primary/50"
          style={{ left: `${progress}%` }}
        >
          <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-3 h-3 bg-primary rounded-full" />
        </div>

        {/* Insight markers on waveform */}
        {showInsights && insightMarkers.map((marker, i) => {
          const markerPosition = (marker.time / audioDuration) * 100;
          const colorClasses = {
            yellow: 'bg-yellow-500',
            green: 'bg-green-500',
            red: 'bg-red-500',
            orange: 'bg-orange-500',
            blue: 'bg-blue-500'
          };
          return (
            <div
              key={i}
              className="absolute top-0 h-full cursor-pointer group"
              style={{ left: `${markerPosition}%` }}
              onClick={(e) => {
                e.stopPropagation();
                jumpToInsight(marker);
              }}
            >
              <div className={`w-1 h-full ${colorClasses[marker.color]} opacity-50 group-hover:opacity-100`} />
              <div className={`absolute -top-1 left-1/2 -translate-x-1/2 w-4 h-4 ${colorClasses[marker.color]} rounded-full flex items-center justify-center`}>
                <marker.icon className="w-2.5 h-2.5 text-white" />
              </div>
              
              {/* Tooltip on hover */}
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block z-20">
                <div className="bg-slate-900 text-white text-xs rounded-lg px-3 py-2 shadow-xl whitespace-nowrap">
                  <p className="font-semibold">{marker.title}</p>
                  <p className="text-slate-400">{formatTime(marker.time)}</p>
                </div>
              </div>
            </div>
          );
        })}

        {/* Loading overlay */}
        {isLoading && (
          <div className="absolute inset-0 bg-slate-900/50 flex items-center justify-center">
            <Loader2 className="w-8 h-8 text-primary animate-spin" />
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {/* Skip Back */}
          <button 
            onClick={() => skip(-10)}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors text-slate-400 hover:text-white"
            title="Skip back 10s"
          >
            <SkipBack className="w-5 h-5" />
          </button>

          {/* Play/Pause */}
          <button
            onClick={togglePlay}
            disabled={isLoading}
            className="w-12 h-12 bg-primary rounded-full flex items-center justify-center hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            {isPlaying ? (
              <Pause className="w-6 h-6 text-white" />
            ) : (
              <Play className="w-6 h-6 text-white ml-0.5" />
            )}
          </button>

          {/* Skip Forward */}
          <button 
            onClick={() => skip(10)}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors text-slate-400 hover:text-white"
            title="Skip forward 10s"
          >
            <SkipForward className="w-5 h-5" />
          </button>

          {/* Time Display */}
          <div className="text-sm text-slate-400 font-mono ml-2">
            {formatTime(currentTime)} / {formatTime(audioDuration)}
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Playback Speed */}
          <button
            onClick={changePlaybackRate}
            className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm text-white transition-colors"
          >
            {playbackRate}x
          </button>

          {/* Volume */}
          <button
            onClick={toggleMute}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors text-slate-400 hover:text-white"
          >
            {isMuted ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Active Insight Display */}
      <AnimatePresence>
        {showInsights && activeInsight && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className={`p-4 rounded-lg border ${
              activeInsight.color === 'yellow' ? 'bg-yellow-500/10 border-yellow-500/30' :
              activeInsight.color === 'green' ? 'bg-green-500/10 border-green-500/30' :
              activeInsight.color === 'red' ? 'bg-red-500/10 border-red-500/30' :
              'bg-orange-500/10 border-orange-500/30'
            }`}
          >
            <div className="flex items-start gap-3">
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
                activeInsight.color === 'yellow' ? 'bg-yellow-500/20' :
                activeInsight.color === 'green' ? 'bg-green-500/20' :
                activeInsight.color === 'red' ? 'bg-red-500/20' :
                'bg-orange-500/20'
              }`}>
                <activeInsight.icon className={`w-5 h-5 ${
                  activeInsight.color === 'yellow' ? 'text-yellow-400' :
                  activeInsight.color === 'green' ? 'text-green-400' :
                  activeInsight.color === 'red' ? 'text-red-400' :
                  'text-orange-400'
                }`} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-1">
                  <h5 className="font-semibold text-white">{activeInsight.title}</h5>
                  <span className="text-xs text-slate-400 flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {formatTime(activeInsight.time)}
                  </span>
                </div>
                {activeInsight.moment && (
                  <p className="text-sm text-slate-400 mb-2 italic">"{activeInsight.moment}"</p>
                )}
                <p className="text-sm text-slate-300">{activeInsight.content}</p>
                {activeInsight.suggestion && (
                  <div className="mt-2 p-2 bg-slate-800/50 rounded text-xs text-slate-300">
                    <span className="text-primary font-medium">Better approach: </span>
                    {activeInsight.suggestion}
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Insight Timeline */}
      {showInsights && insightMarkers.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs text-slate-500 uppercase tracking-wide">AI Coaching Insights Timeline</p>
          <div className="flex flex-wrap gap-2">
            {insightMarkers.map((marker, i) => {
              const colorClasses = {
                yellow: 'bg-yellow-500/20 text-yellow-400 hover:bg-yellow-500/30',
                green: 'bg-green-500/20 text-green-400 hover:bg-green-500/30',
                red: 'bg-red-500/20 text-red-400 hover:bg-red-500/30',
                orange: 'bg-orange-500/20 text-orange-400 hover:bg-orange-500/30'
              };
              return (
                <button
                  key={i}
                  onClick={() => jumpToInsight(marker)}
                  className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs transition-colors ${colorClasses[marker.color]} ${
                    activeInsight === marker ? 'ring-2 ring-white/20' : ''
                  }`}
                >
                  <marker.icon className="w-3 h-3" />
                  <span>{marker.title}</span>
                  <span className="opacity-60">{formatTime(marker.time)}</span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* No insights message */}
      {showInsights && insightMarkers.length === 0 && coaching && (
        <div className="text-center py-4 text-slate-500 text-sm">
          <Lightbulb className="w-8 h-8 mx-auto mb-2 opacity-30" />
          <p>No specific moment insights available</p>
          <p className="text-xs">View the AI Coaching tab for general recommendations</p>
        </div>
      )}
    </div>
  );
};

export default WaveformPlayer;
