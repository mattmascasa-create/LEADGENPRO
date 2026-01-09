import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import { 
  Phone, X, Save, MessageSquare, Calendar, ThumbsDown, 
  UserX, AlertTriangle, PhoneOff, Users, Clock, CheckCircle,
  ArrowRight, FileText
} from 'lucide-react';
import { toast } from 'react-toastify';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Disposition options with icons and colors
const DISPOSITION_OPTIONS = [
  { value: 'No Answer', icon: PhoneOff, color: 'bg-slate-100 text-slate-700', description: 'No one picked up' },
  { value: 'Left Voicemail', icon: MessageSquare, color: 'bg-blue-100 text-blue-700', description: 'Left a message' },
  { value: 'Gatekeeper', icon: Users, color: 'bg-purple-100 text-purple-700', description: 'Spoke to receptionist/assistant' },
  { value: 'Bad Number', icon: AlertTriangle, color: 'bg-red-100 text-red-700', description: 'Number is disconnected or wrong' },
  { value: 'No Longer with Company', icon: UserX, color: 'bg-orange-100 text-orange-700', description: 'Contact has left the company' },
  { value: 'Wrong POC', icon: UserX, color: 'bg-yellow-100 text-yellow-700', description: 'Wrong person/contact' },
  { value: 'Not Interested', icon: ThumbsDown, color: 'bg-red-100 text-red-700', description: 'Declined our services' },
  { value: 'Referral', icon: ArrowRight, color: 'bg-green-100 text-green-700', description: 'Referred to another contact' },
  { value: 'Call Back', icon: Clock, color: 'bg-cyan-100 text-cyan-700', description: 'Requested callback at specific time' },
  { value: 'Set Meeting', icon: Calendar, color: 'bg-green-100 text-green-700', description: 'Scheduled a meeting/appointment' },
  { value: 'Sent Info', icon: FileText, color: 'bg-indigo-100 text-indigo-700', description: 'Sent information/materials' },
  { value: 'DNC - Do Not Call', icon: PhoneOff, color: 'bg-red-200 text-red-800', description: 'Requested to not be contacted' },
];

const CallDispositionModal = ({ 
  isOpen, 
  onClose, 
  callId, 
  leadInfo,
  callDuration,
  onDispositionSaved 
}) => {
  const [selectedDisposition, setSelectedDisposition] = useState('');
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setSelectedDisposition('');
      setNotes('');
    }
  }, [isOpen]);

  const formatDuration = (seconds) => {
    if (!seconds) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleSave = async () => {
    if (!selectedDisposition) {
      toast.error('Please select a disposition');
      return;
    }

    setSaving(true);
    try {
      const token = localStorage.getItem('token');
      await axios.put(
        `${API_URL}/api/calls/${callId}/disposition`,
        null,
        {
          params: { disposition: selectedDisposition, notes },
          headers: { Authorization: `Bearer ${token}` }
        }
      );
      
      toast.success('Call disposition saved!');
      onDispositionSaved?.();
      onClose();
    } catch (error) {
      console.error('Failed to save disposition:', error);
      toast.error('Failed to save disposition');
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          className="bg-white rounded-3xl w-full max-w-3xl max-h-[90vh] overflow-y-auto shadow-2xl"
        >
          {/* Header */}
          <div className="p-8 border-b border-border bg-gradient-to-r from-green-50 to-blue-50">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-5">
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
                  <Phone className="w-8 h-8 text-green-600" />
                </div>
                <div>
                  <h2 className="text-2xl font-bold text-foreground">Call Complete</h2>
                  {leadInfo && (
                    <p className="text-lg text-secondary">
                      {leadInfo.first_name} {leadInfo.last_name} - {leadInfo.company}
                    </p>
                  )}
                </div>
              </div>
              <div className="text-right">
                <p className="text-4xl font-bold text-green-600">{formatDuration(callDuration)}</p>
                <p className="text-sm text-secondary">Call Duration</p>
              </div>
            </div>
          </div>

          {/* Disposition Selection */}
          <div className="p-8">
            <h3 className="font-semibold text-lg text-foreground mb-5">What was the outcome of this call?</h3>
            
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8">
              {DISPOSITION_OPTIONS.map((option) => {
                const Icon = option.icon;
                const isSelected = selectedDisposition === option.value;
                return (
                  <button
                    key={option.value}
                    onClick={() => setSelectedDisposition(option.value)}
                    className={`p-5 rounded-2xl border-2 transition-all text-left ${
                      isSelected 
                        ? 'border-primary bg-primary/5 ring-2 ring-primary/20' 
                        : 'border-border hover:border-primary/50 hover:bg-slate-50'
                    }`}
                  >
                    <div className="flex items-center gap-3 mb-2">
                      <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${option.color}`}>
                        <Icon className="w-5 h-5" />
                      </div>
                      {isSelected && <CheckCircle className="w-6 h-6 text-primary ml-auto" />}
                    </div>
                    <p className="font-semibold">{option.value}</p>
                    <p className="text-sm text-secondary mt-1">{option.description}</p>
                  </button>
                );
              })}
            </div>

            {/* Notes - Larger */}
            <div className="mb-8">
              <label className="block font-semibold text-lg text-foreground mb-3">
                Call Notes
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Add details about this call... (e.g., 'Talked to assistant, said to call back at 2 PM')"
                rows={6}
                className="w-full px-5 py-4 border-2 border-border rounded-2xl focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary resize-none text-lg"
              />
              <p className="text-xs text-secondary mt-2">
                This will be logged in the lead's activity history
              </p>
            </div>

            {/* Preview */}
            {selectedDisposition && (
              <div className="bg-slate-50 rounded-xl p-4 mb-6">
                <p className="text-sm font-medium text-secondary mb-2">Activity Preview:</p>
                <p className="text-foreground">
                  <span className="font-semibold">Call - {selectedDisposition}</span>
                  {notes && <span className="text-secondary"> - {notes}</span>}
                </p>
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-3">
              <button
                onClick={onClose}
                className="flex-1 px-4 py-3 border border-border rounded-xl hover:bg-slate-50 transition-colors font-medium"
              >
                Skip for Now
              </button>
              <button
                onClick={handleSave}
                disabled={!selectedDisposition || saving}
                className="flex-1 px-4 py-3 bg-primary text-white rounded-xl hover:bg-primary/90 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {saving ? (
                  <>Saving...</>
                ) : (
                  <>
                    <Save className="w-4 h-4" />
                    Save Disposition
                  </>
                )}
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default CallDispositionModal;
