import React, { useState } from 'react';
import { 
  Mail, X, Send, Users, Paperclip, User
} from 'lucide-react';
import { toast } from 'react-toastify';
import { motion, AnimatePresence } from 'framer-motion';

const EmailModal = ({ isOpen, onClose, leads = [], singleLead = null }) => {
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [isSending, setIsSending] = useState(false);

  // Get recipients - either single lead or multiple leads
  const recipients = singleLead ? [singleLead] : leads;
  const recipientCount = recipients.length;

  const handleSendEmail = () => {
    if (!subject.trim()) {
      toast.error('Please enter a subject');
      return;
    }
    if (!body.trim()) {
      toast.error('Please enter a message');
      return;
    }
    if (recipientCount === 0) {
      toast.error('No recipients selected');
      return;
    }

    setIsSending(true);

    // Build email addresses
    const emails = recipients.map(lead => lead.email).filter(Boolean);
    
    if (emails.length === 0) {
      toast.error('No valid email addresses found');
      setIsSending(false);
      return;
    }

    // Create mailto link
    const mailtoLink = `mailto:${emails.join(',')}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    
    // Open default email client
    window.location.href = mailtoLink;
    
    toast.success(`Opening email client for ${emails.length} recipient(s)`);
    setIsSending(false);
    
    // Reset form
    setSubject('');
    setBody('');
    onClose();
  };

  // Email templates
  const templates = [
    {
      name: 'Introduction',
      subject: 'Introduction from [Your Company]',
      body: `Hi {first_name},

I hope this email finds you well. I wanted to reach out and introduce myself.

I noticed that {company} might benefit from our services, and I'd love to schedule a quick call to discuss how we can help.

Would you be available for a 15-minute call this week?

Best regards,
[Your Name]`
    },
    {
      name: 'Follow Up',
      subject: 'Following up on our conversation',
      body: `Hi {first_name},

I wanted to follow up on our recent conversation and see if you had any questions.

Please let me know if there's anything I can help with or if you'd like to schedule another call.

Best regards,
[Your Name]`
    },
    {
      name: 'Meeting Request',
      subject: 'Meeting Request - {company}',
      body: `Hi {first_name},

I'd like to schedule a meeting to discuss how we can work together.

Please let me know your availability for the upcoming week, and I'll send over a calendar invite.

Looking forward to connecting!

Best regards,
[Your Name]`
    }
  ];

  const applyTemplate = (template) => {
    let newSubject = template.subject;
    let newBody = template.body;
    
    // If single recipient, personalize the template
    if (singleLead) {
      newSubject = newSubject.replace('{company}', singleLead.company || 'your company');
      newBody = newBody
        .replace(/{first_name}/g, singleLead.first_name || 'there')
        .replace(/{company}/g, singleLead.company || 'your company');
    }
    
    setSubject(newSubject);
    setBody(newBody);
    toast.success('Template applied');
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
        onClick={(e) => e.target === e.currentTarget && onClose()}
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl mx-4 overflow-hidden"
        >
          {/* Header */}
          <div className="bg-blue-500 p-6 text-white">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold flex items-center gap-2">
                <Mail className="w-6 h-6" />
                Compose Email
              </h2>
              <button onClick={onClose} className="p-1 hover:bg-white/20 rounded-full transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Recipients */}
            <div className="flex items-center gap-2 bg-white/10 rounded-lg p-3">
              {recipientCount === 1 ? (
                <>
                  <User className="w-5 h-5" />
                  <span>{recipients[0]?.first_name} {recipients[0]?.last_name}</span>
                  <span className="text-white/70">({recipients[0]?.email})</span>
                </>
              ) : (
                <>
                  <Users className="w-5 h-5" />
                  <span>{recipientCount} recipients selected</span>
                </>
              )}
            </div>
          </div>

          {/* Body */}
          <div className="p-6 space-y-4">
            {/* Quick Templates */}
            <div>
              <label className="block text-sm font-medium text-secondary mb-2">Quick Templates</label>
              <div className="flex gap-2 flex-wrap">
                {templates.map((template, idx) => (
                  <button
                    key={idx}
                    onClick={() => applyTemplate(template)}
                    className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 rounded-full text-sm font-medium transition-colors"
                  >
                    {template.name}
                  </button>
                ))}
              </div>
            </div>

            {/* Subject */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Subject *</label>
              <input
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder="Enter email subject"
                className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Body */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Message *</label>
              <textarea
                value={body}
                onChange={(e) => setBody(e.target.value)}
                placeholder="Type your message here..."
                rows={10}
                className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              />
            </div>

            {/* Bulk email note */}
            {recipientCount > 1 && (
              <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                <p className="text-sm text-yellow-800">
                  <strong>Note:</strong> This will open your email client with all {recipientCount} recipients in the "To" field. 
                  You may want to use BCC for privacy.
                </p>
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-3 pt-4">
              <button
                onClick={onClose}
                className="flex-1 py-3 border border-border rounded-xl font-medium hover:bg-slate-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSendEmail}
                disabled={isSending || !subject.trim() || !body.trim()}
                className="flex-1 py-3 bg-blue-500 text-white rounded-xl font-semibold hover:bg-blue-600 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
              >
                <Send className="w-4 h-4" />
                {isSending ? 'Opening...' : `Send to ${recipientCount} recipient${recipientCount > 1 ? 's' : ''}`}
              </button>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default EmailModal;
