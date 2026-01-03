import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bot, X, Upload, Globe, UserPlus, Target, Phone, Calendar, ChevronRight, Sparkles, CheckCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const AICopilot = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const navigate = useNavigate();

  const steps = [
    {
      icon: Target,
      title: 'Welcome to Lead Gen!',
      description: 'I\'ll guide you through getting leads and booking meetings',
      actions: [
        { label: 'Import Contacts', action: () => navigate('/leads?action=import'), icon: Upload },
        { label: 'Scrape Website', action: () => navigate('/leads?action=scrape'), icon: Globe },
        { label: 'Add Manual Lead', action: () => navigate('/leads?action=create'), icon: UserPlus }
      ]
    },
    {
      icon: Phone,
      title: 'Assign Leads to Team',
      description: 'Distribute leads to your SDRs for calling',
      actions: [
        { label: 'Distribute Leads', action: () => navigate('/admin/distribute'), icon: Target },
        { label: 'View Call Lists', action: () => navigate('/call-lists'), icon: Phone }
      ]
    },
    {
      icon: Calendar,
      title: 'Make Calls & Book Meetings',
      description: 'Your team calls leads and schedules meetings',
      actions: [
        { label: 'Start Calling', action: () => navigate('/call-lists'), icon: Phone },
        { label: 'View Calendar', action: () => navigate('/appointments'), icon: Calendar }
      ]
    },
    {
      icon: CheckCircle,
      title: 'Track Results',
      description: 'Monitor meeting bookings and conversions',
      actions: [
        { label: 'View Analytics', action: () => navigate('/analytics'), icon: Target },
        { label: 'See Pipeline', action: () => navigate('/pipeline'), icon: Target }
      ]
    }
  ];

  return (
    <>
      {/* Floating Copilot Button - Only show on first visit */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-28 left-6 w-12 h-12 bg-gradient-to-br from-primary to-accent text-white rounded-full shadow-xl hover:scale-110 transition-transform duration-200 flex items-center justify-center z-40"
        title="Getting Started Guide"
      >
        <Bot className="w-6 h-6" />
      </button>

      {/* Copilot Panel */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, x: -20, scale: 0.95 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: -20, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className="fixed bottom-44 left-6 w-96 bg-white rounded-xl shadow-2xl border border-border overflow-hidden z-50"
          >
            {/* Header */}
            <div className="bg-gradient-to-r from-primary to-accent p-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Bot className="w-5 h-5 text-white" />
                <h3 className="text-white font-semibold">AI Lead Gen Copilot</h3>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="text-white/80 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Progress Steps */}
            <div className="p-4 border-b border-border bg-slate-50">
              <div className="flex items-center justify-between mb-2">
                {steps.map((_, index) => (
                  <React.Fragment key={index}>
                    <div
                      className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold transition-all ${
                        index <= currentStep
                          ? 'bg-primary text-white'
                          : 'bg-slate-200 text-slate-400'
                      }`}
                    >
                      {index + 1}
                    </div>
                    {index < steps.length - 1 && (
                      <div className={`flex-1 h-1 mx-2 rounded-full transition-all ${
                        index < currentStep ? 'bg-primary' : 'bg-slate-200'
                      }`} />
                    )}
                  </React.Fragment>
                ))}
              </div>
            </div>

            {/* Content */}
            <div className="p-6">
              <AnimatePresence mode="wait">
                <motion.div
                  key={currentStep}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.2 }}
                >
                  {(() => {
                    const step = steps[currentStep];
                    const Icon = step.icon;
                    return (
                      <>
                        <div className="flex items-start gap-3 mb-6">
                          <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center flex-shrink-0">
                            <Icon className="w-6 h-6 text-primary" />
                          </div>
                          <div>
                            <h4 className="text-lg font-bold text-foreground mb-1">{step.title}</h4>
                            <p className="text-sm text-secondary">{step.description}</p>
                          </div>
                        </div>

                        <div className="space-y-2">
                          {step.actions.map((action, index) => {
                            const ActionIcon = action.icon;
                            return (
                              <button
                                key={index}
                                onClick={() => {
                                  action.action();
                                  setIsOpen(false);
                                }}
                                className="w-full flex items-center justify-between p-3 bg-slate-50 hover:bg-slate-100 border border-border rounded-lg transition-all group"
                              >
                                <div className="flex items-center gap-3">
                                  <ActionIcon className="w-5 h-5 text-primary" />
                                  <span className="font-medium text-foreground">{action.label}</span>
                                </div>
                                <ChevronRight className="w-5 h-5 text-secondary group-hover:text-primary transition-colors" />
                              </button>
                            );
                          })}
                        </div>
                      </>
                    );
                  })()}
                </motion.div>
              </AnimatePresence>
            </div>

            {/* Navigation */}
            <div className="border-t border-border p-4 bg-slate-50 flex gap-2">
              <button
                onClick={() => setCurrentStep(Math.max(0, currentStep - 1))}
                disabled={currentStep === 0}
                className="flex-1 py-2 px-4 border border-border rounded-lg font-medium hover:bg-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <button
                onClick={() => setCurrentStep(Math.min(steps.length - 1, currentStep + 1))}
                disabled={currentStep === steps.length - 1}
                className="flex-1 py-2 px-4 bg-primary text-white rounded-lg font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};

export default AICopilot;