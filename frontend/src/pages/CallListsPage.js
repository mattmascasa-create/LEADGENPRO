import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Phone, CheckCircle, XCircle, Clock, Calendar, MessageSquare } from 'lucide-react';
import { toast } from 'react-toastify';
import DashboardLayout from '@/components/DashboardLayout';
import { motion } from 'framer-motion';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const CallListsPage = () => {
  const [callList, setCallList] = useState([]);
  const [selectedLead, setSelectedLead] = useState(null);
  const [outcome, setOutcome] = useState('');
  const [notes, setNotes] = useState('');
  const [meetingDate, setMeetingDate] = useState('');
  const [logging, setLogging] = useState(false);

  useEffect(() => {
    fetchCallList();
  }, []);

  const fetchCallList = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/call-list`);
      setCallList(response.data.call_list);
    } catch (error) {
      toast.error('Failed to load call list');
    }
  };

  const handleLogCall = async () => {
    if (!outcome) {
      toast.error('Please select an outcome');
      return;
    }

    setLogging(true);
    try {
      await axios.post(`${API_URL}/api/call-log`, {
        lead_id: selectedLead.lead.id,
        outcome,
        notes,
        meeting_scheduled_at: meetingDate ? new Date(meetingDate).toISOString() : null
      });
      toast.success('Call logged successfully!');
      setSelectedLead(null);
      setOutcome('');
      setNotes('');
      setMeetingDate('');
      fetchCallList();
    } catch (error) {
      toast.error('Failed to log call');
    } finally {
      setLogging(false);
    }
  };

  const getOutcomeIcon = (outcome) => {
    switch (outcome) {
      case 'contacted':
        return <CheckCircle className="w-5 h-5 text-green-600" />;
      case 'no_answer':
        return <XCircle className="w-5 h-5 text-red-600" />;
      case 'voicemail':
        return <MessageSquare className="w-5 h-5 text-yellow-600" />;
      case 'meeting_scheduled':
        return <Calendar className="w-5 h-5 text-primary" />;
      default:
        return <Clock className="w-5 h-5 text-secondary" />;
    }
  };

  return (
    <DashboardLayout>
      <div>
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-foreground mb-2">Daily Call List</h1>
          <p className="text-secondary">Your assigned leads for today - Goal: Book meetings!</p>
        </div>

        {/* Stats */}
        <div className="grid md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white p-4 rounded-lg border border-border">
            <div className="text-2xl font-bold metric-value text-primary">{callList.length}</div>
            <div className="text-sm text-secondary">Total Calls</div>
          </div>
          <div className="bg-white p-4 rounded-lg border border-border">
            <div className="text-2xl font-bold metric-value text-green-600">
              {callList.filter(c => c.call_status === 'contacted').length}
            </div>
            <div className="text-sm text-secondary">Contacted</div>
          </div>
          <div className="bg-white p-4 rounded-lg border border-border">
            <div className="text-2xl font-bold metric-value text-accent">
              {callList.filter(c => c.call_status === 'meeting_scheduled').length}
            </div>
            <div className="text-sm text-secondary">Meetings Booked</div>
          </div>
          <div className="bg-white p-4 rounded-lg border border-border">
            <div className="text-2xl font-bold metric-value text-secondary">
              {callList.filter(c => !c.call_status).length}
            </div>
            <div className="text-sm text-secondary">Not Called</div>
          </div>
        </div>

        {/* Call List */}
        <div className="grid lg:grid-cols-2 gap-4">
          {callList.map((item, index) => (
            <motion.div
              key={item.lead.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className="bg-white p-6 rounded-xl border border-border hover:border-primary transition-all"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <h3 className="text-lg font-bold text-foreground mb-1">
                    {item.lead.first_name} {item.lead.last_name}
                  </h3>
                  <p className="text-sm text-secondary mb-2">{item.lead.company} • {item.lead.title || 'Contact'}</p>
                  <div className="flex items-center gap-4 text-sm">
                    <a href={`tel:${item.lead.phone}`} className="flex items-center gap-1 text-primary hover:underline">
                      <Phone className="w-4 h-4" />
                      {item.lead.phone || 'No phone'}
                    </a>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-bold metric-value text-primary mb-1">{item.lead.score}</div>
                  <div className="text-xs text-secondary">Score</div>
                </div>
              </div>

              {item.call_status && (
                <div className="mb-4 p-3 bg-slate-50 rounded-lg flex items-center gap-2">
                  {getOutcomeIcon(item.call_status)}
                  <span className="text-sm font-medium capitalize">{item.call_status.replace('_', ' ')}</span>
                </div>
              )}

              <button
                onClick={() => setSelectedLead(item)}
                className="w-full py-2 bg-primary text-white rounded-lg font-semibold hover:bg-primary/90 transition-all flex items-center justify-center gap-2"
              >
                <Phone className="w-4 h-4" />
                {item.call_status ? 'Update Call' : 'Log Call'}
              </button>
            </motion.div>
          ))}
        </div>

        {/* Log Call Modal */}
        {selectedLead && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="bg-white rounded-xl p-8 max-w-lg w-full"
            >
              <h3 className="text-2xl font-bold text-foreground mb-4">
                Log Call - {selectedLead.lead.first_name} {selectedLead.lead.last_name}
              </h3>

              <div className="space-y-4 mb-6">
                <div>
                  <label className="block text-sm font-medium mb-2">Call Outcome</label>
                  <select
                    value={outcome}
                    onChange={(e) => setOutcome(e.target.value)}
                    className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    <option value="">Select outcome...</option>
                    <option value="contacted">Contacted</option>
                    <option value="no_answer">No Answer</option>
                    <option value="voicemail">Left Voicemail</option>
                    <option value="wrong_number">Wrong Number</option>
                    <option value="meeting_scheduled">Meeting Scheduled ✓</option>
                  </select>
                </div>

                {outcome === 'meeting_scheduled' && (
                  <div>
                    <label className="block text-sm font-medium mb-2">Meeting Date & Time</label>
                    <input
                      type="datetime-local"
                      value={meetingDate}
                      onChange={(e) => setMeetingDate(e.target.value)}
                      className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                  </div>
                )}

                <div>
                  <label className="block text-sm font-medium mb-2">Notes</label>
                  <textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    rows={3}
                    placeholder="Call notes, follow-up actions..."
                    className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary resize-none"
                  />
                </div>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => setSelectedLead(null)}
                  className="flex-1 py-3 border-2 border-border rounded-lg font-semibold hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleLogCall}
                  disabled={logging || !outcome}
                  className="flex-1 py-3 bg-primary text-white rounded-lg font-semibold hover:bg-primary/90 transition-all disabled:opacity-50"
                >
                  {logging ? 'Logging...' : 'Save'}
                </button>
              </div>
            </motion.div>
          </div>
        )}

        {callList.length === 0 && (
          <div className="text-center py-16">
            <Phone className="w-16 h-16 text-secondary mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-foreground mb-2">No calls assigned yet</h3>
            <p className="text-secondary">Contact your admin to get leads assigned</p>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
};

export default CallListsPage;