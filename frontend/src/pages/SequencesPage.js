import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import { Plus, Mail, Clock, Zap, Play, Pause, Edit, Trash2, Copy } from 'lucide-react';
import { toast } from 'react-toastify';
import DashboardLayout from '@/components/DashboardLayout';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const SequencesPage = () => {
  const [sequences, setSequences] = useState([]);
  const [showBuilder, setShowBuilder] = useState(false);
  const [editingSequence, setEditingSequence] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    steps: []
  });

  useEffect(() => {
    fetchSequences();
  }, []);

  const fetchSequences = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/sequences`);
      setSequences(response.data);
    } catch (error) {
      toast.error('Failed to load sequences');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API_URL}/api/sequences`, formData);
      toast.success('Sequence created successfully!');
      setShowBuilder(false);
      setFormData({ name: '', description: '', steps: [] });
      fetchSequences();
    } catch (error) {
      toast.error('Failed to create sequence');
    }
  };

  const addStep = () => {
    setFormData({
      ...formData,
      steps: [...formData.steps, {
        type: 'email',
        delay_days: 0,
        subject: '',
        body: ''
      }]
    });
  };

  const updateStep = (index, field, value) => {
    const newSteps = [...formData.steps];
    newSteps[index][field] = value;
    setFormData({ ...formData, steps: newSteps });
  };

  const removeStep = (index) => {
    setFormData({
      ...formData,
      steps: formData.steps.filter((_, i) => i !== index)
    });
  };

  return (
    <DashboardLayout>
      <div>
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-4xl font-bold text-foreground mb-2">Email Sequences</h1>
            <p className="text-secondary">Automate your outreach with multi-step email campaigns</p>
          </div>
          <button
            onClick={() => setShowBuilder(!showBuilder)}
            className="px-6 py-3 bg-primary text-white rounded-lg font-semibold hover:bg-primary/90 transition-all duration-200 flex items-center gap-2"
          >
            <Plus className="w-5 h-5" />
            Create Sequence
          </button>
        </div>

        {/* Sequence Builder */}
        {showBuilder && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white p-8 rounded-xl border border-border mb-8 shadow-lg"
          >
            <h3 className="text-2xl font-bold text-foreground mb-6">Build Your Sequence</h3>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">Sequence Name</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({...formData, name: e.target.value})}
                    required
                    placeholder="e.g., SaaS Demo Follow-up"
                    className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">Description</label>
                  <input
                    type="text"
                    value={formData.description}
                    onChange={(e) => setFormData({...formData, description: e.target.value})}
                    placeholder="What's this sequence for?"
                    className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
              </div>

              {/* Sequence Steps */}
              <div>
                <div className="flex items-center justify-between mb-4">
                  <h4 className="text-lg font-semibold text-foreground">Email Steps</h4>
                  <button
                    type="button"
                    onClick={addStep}
                    className="px-4 py-2 border-2 border-primary text-primary rounded-lg font-medium hover:bg-primary/10 transition-colors flex items-center gap-2"
                  >
                    <Plus className="w-4 h-4" />
                    Add Step
                  </button>
                </div>

                <div className="space-y-4">
                  {formData.steps.map((step, index) => (
                    <div key={index} className="relative">
                      {index > 0 && (
                        <div className="absolute left-6 -top-4 flex items-center gap-2">
                          <div className="w-px h-4 bg-primary"></div>
                          <Clock className="w-4 h-4 text-primary" />
                          <span className="text-sm text-secondary">
                            Wait {step.delay_days} {step.delay_days === 1 ? 'day' : 'days'}
                          </span>
                        </div>
                      )}
                      <div className="bg-slate-50 p-6 rounded-lg border-2 border-border">
                        <div className="flex items-start gap-4">
                          <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center flex-shrink-0">
                            <Mail className="w-6 h-6 text-primary" />
                          </div>
                          <div className="flex-1 space-y-4">
                            <div className="flex items-center gap-4">
                              <span className="text-sm font-semibold text-foreground">Step {index + 1}</span>
                              {index > 0 && (
                                <div className="flex items-center gap-2">
                                  <label className="text-sm text-secondary">Delay:</label>
                                  <input
                                    type="number"
                                    min="0"
                                    value={step.delay_days}
                                    onChange={(e) => updateStep(index, 'delay_days', parseInt(e.target.value))}
                                    className="w-20 px-3 py-1 border border-border rounded text-sm"
                                  />
                                  <span className="text-sm text-secondary">days</span>
                                </div>
                              )}
                              <button
                                type="button"
                                onClick={() => removeStep(index)}
                                className="ml-auto p-2 text-destructive hover:bg-destructive/10 rounded transition-colors"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                            <input
                              type="text"
                              placeholder="Email Subject"
                              value={step.subject}
                              onChange={(e) => updateStep(index, 'subject', e.target.value)}
                              required
                              className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                            />
                            <textarea
                              placeholder="Email Body"
                              value={step.body}
                              onChange={(e) => updateStep(index, 'body', e.target.value)}
                              required
                              rows={4}
                              className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary resize-none"
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}

                  {formData.steps.length === 0 && (
                    <div className="text-center py-12 bg-slate-50 rounded-lg border-2 border-dashed border-border">
                      <Mail className="w-12 h-12 text-secondary mx-auto mb-3" />
                      <p className="text-secondary">No steps yet. Click "Add Step" to start building your sequence.</p>
                    </div>
                  )}
                </div>
              </div>

              <div className="flex gap-3 pt-6 border-t border-border">
                <button
                  type="submit"
                  disabled={formData.steps.length === 0}
                  className="flex-1 py-3 bg-primary text-white rounded-lg font-semibold hover:bg-primary/90 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Create Sequence
                </button>
                <button
                  type="button"
                  onClick={() => setShowBuilder(false)}
                  className="px-8 py-3 border-2 border-border rounded-lg font-semibold hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </form>
          </motion.div>
        )}

        {/* Sequences List */}
        <div>
          <h3 className="text-2xl font-semibold text-foreground mb-4">Your Sequences</h3>
          <div className="grid md:grid-cols-2 gap-6">
            {sequences.map((sequence, index) => (
              <motion.div
                key={sequence.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                className="bg-white p-6 rounded-xl border border-border hover:border-primary transition-all duration-200"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <h4 className="text-xl font-bold text-foreground mb-2">{sequence.name}</h4>
                    <p className="text-sm text-secondary">{sequence.description}</p>
                  </div>
                  <div className={`px-3 py-1 rounded-full text-xs font-semibold ${
                    sequence.active ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-600'
                  }`}>
                    {sequence.active ? 'Active' : 'Paused'}
                  </div>
                </div>

                <div className="mb-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Mail className="w-4 h-4 text-primary" />
                    <span className="text-sm font-medium text-foreground">
                      {sequence.steps?.length || 0} Email Steps
                    </span>
                  </div>
                  {sequence.steps && sequence.steps.length > 0 && (
                    <div className="pl-6 space-y-2">
                      {sequence.steps.map((step, stepIndex) => (
                        <div key={stepIndex} className="text-sm text-secondary flex items-center gap-2">
                          <div className="w-2 h-2 bg-primary rounded-full"></div>
                          {stepIndex > 0 && `Day ${step.delay_days}: `}
                          {step.subject || 'Email step'}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="flex gap-2">
                  <button className="flex-1 px-4 py-2 border border-border rounded-lg text-sm font-medium hover:bg-slate-50 transition-colors flex items-center justify-center gap-2">
                    {sequence.active ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                    {sequence.active ? 'Pause' : 'Activate'}
                  </button>
                  <button className="px-4 py-2 border border-border rounded-lg text-sm font-medium hover:bg-slate-50 transition-colors">
                    <Edit className="w-4 h-4" />
                  </button>
                  <button className="px-4 py-2 border border-border rounded-lg text-sm font-medium hover:bg-slate-50 transition-colors">
                    <Copy className="w-4 h-4" />
                  </button>
                </div>
              </motion.div>
            ))}

            {sequences.length === 0 && (
              <div className="col-span-full text-center py-16">
                <Zap className="w-16 h-16 text-secondary mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-foreground mb-2">No sequences yet</h3>
                <p className="text-secondary mb-6">Create your first email sequence to automate your outreach</p>
                <button
                  onClick={() => setShowBuilder(true)}
                  className="px-6 py-3 bg-primary text-white rounded-lg font-semibold hover:bg-primary/90 transition-all duration-200 inline-flex items-center gap-2"
                >
                  <Plus className="w-5 h-5" />
                  Create Your First Sequence
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default SequencesPage;