import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import axios from 'axios';
import { motion } from 'framer-motion';
import { CheckCircle, ChevronRight, Sparkles, Users, Target, Mail } from 'lucide-react';
import { toast } from 'react-toastify';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const OnboardingWizard = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [step, setStep] = useState(1);
  const [data, setData] = useState({
    goals: [],
    team_size: '',
    industry: ''
  });

  const steps = [
    { number: 1, title: 'Welcome', icon: Sparkles },
    { number: 2, title: 'Goals', icon: Target },
    { number: 3, title: 'Team', icon: Users },
    { number: 4, title: 'Ready', icon: CheckCircle }
  ];

  const handleComplete = async () => {
    try {
      await axios.put(`${API_URL}/api/auth/onboarding`);
      toast.success('Setup complete! Welcome to LeadGen Pro');
      navigate('/dashboard');
    } catch (error) {
      toast.error('Failed to complete onboarding');
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-6">
      <div className="w-full max-w-4xl">
        {/* Progress Bar */}
        <div className="mb-12">
          <div className="flex items-center justify-between mb-4">
            {steps.map((s, index) => {
              const Icon = s.icon;
              const isActive = step === s.number;
              const isComplete = step > s.number;
              
              return (
                <React.Fragment key={s.number}>
                  <div className="flex flex-col items-center">
                    <div className={`
                      w-12 h-12 rounded-full flex items-center justify-center mb-2 transition-all duration-300
                      ${isComplete ? 'bg-primary text-white' : isActive ? 'bg-primary text-white' : 'bg-slate-200 text-slate-400'}
                    `}>
                      <Icon className="w-6 h-6" />
                    </div>
                    <span className={`text-sm font-medium ${isActive || isComplete ? 'text-foreground' : 'text-secondary'}`}>
                      {s.title}
                    </span>
                  </div>
                  {index < steps.length - 1 && (
                    <div className={`flex-1 h-1 mx-4 rounded-full transition-all duration-300 ${
                      step > s.number ? 'bg-primary' : 'bg-slate-200'
                    }`} />
                  )}
                </React.Fragment>
              );
            })}
          </div>
        </div>

        {/* Content */}
        <motion.div
          key={step}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          className="bg-white rounded-2xl border border-border p-12 shadow-lg"
        >
          {step === 1 && (
            <div className="text-center">
              <div className="w-20 h-20 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-6">
                <Sparkles className="w-10 h-10 text-primary" />
              </div>
              <h2 className="text-4xl font-bold text-foreground mb-4">Welcome to LeadGen Pro, {user?.full_name}!</h2>
              <p className="text-lg text-secondary mb-8">
                Let's get you set up in just a few quick steps. This will take less than 2 minutes.
              </p>
              <button
                onClick={() => setStep(2)}
                className="px-8 py-4 bg-primary text-white rounded-lg font-semibold hover:bg-primary/90 transition-all duration-200 inline-flex items-center gap-2"
              >
                Let's Get Started
                <ChevronRight className="w-5 h-5" />
              </button>
            </div>
          )}

          {step === 2 && (
            <div>
              <h2 className="text-3xl font-bold text-foreground mb-3">What are your main goals?</h2>
              <p className="text-secondary mb-8">Select all that apply</p>
              <div className="grid md:grid-cols-2 gap-4 mb-8">
                {[
                  { id: 'generate_leads', label: 'Generate More Leads', icon: Target },
                  { id: 'automate_outreach', label: 'Automate Outreach', icon: Mail },
                  { id: 'track_pipeline', label: 'Track Sales Pipeline', icon: Users },
                  { id: 'improve_conversion', label: 'Improve Conversion Rate', icon: CheckCircle }
                ].map((goal) => {
                  const Icon = goal.icon;
                  const isSelected = data.goals.includes(goal.id);
                  return (
                    <button
                      key={goal.id}
                      onClick={() => {
                        setData({
                          ...data,
                          goals: isSelected 
                            ? data.goals.filter(g => g !== goal.id)
                            : [...data.goals, goal.id]
                        });
                      }}
                      className={`
                        p-6 rounded-xl border-2 transition-all duration-200 text-left
                        ${isSelected 
                          ? 'border-primary bg-primary/5' 
                          : 'border-border hover:border-primary/50'
                        }
                      `}
                    >
                      <Icon className={`w-8 h-8 mb-3 ${isSelected ? 'text-primary' : 'text-secondary'}`} />
                      <div className="font-semibold text-foreground">{goal.label}</div>
                    </button>
                  );
                })}
              </div>
              <div className="flex justify-between">
                <button
                  onClick={() => setStep(1)}
                  className="px-6 py-3 border-2 border-border rounded-lg font-medium hover:bg-slate-50 transition-colors"
                >
                  Back
                </button>
                <button
                  onClick={() => setStep(3)}
                  disabled={data.goals.length === 0}
                  className="px-6 py-3 bg-primary text-white rounded-lg font-semibold hover:bg-primary/90 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Continue
                </button>
              </div>
            </div>
          )}

          {step === 3 && (
            <div>
              <h2 className="text-3xl font-bold text-foreground mb-3">Tell us about your team</h2>
              <p className="text-secondary mb-8">This helps us customize your experience</p>
              <div className="space-y-6 mb-8">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">Team Size</label>
                  <select
                    value={data.team_size}
                    onChange={(e) => setData({...data, team_size: e.target.value})}
                    className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    <option value="">Select team size</option>
                    <option value="1-5">1-5 people</option>
                    <option value="6-20">6-20 people</option>
                    <option value="21-50">21-50 people</option>
                    <option value="51+">51+ people</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">Industry</label>
                  <select
                    value={data.industry}
                    onChange={(e) => setData({...data, industry: e.target.value})}
                    className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    <option value="">Select industry</option>
                    <option value="technology">Technology</option>
                    <option value="saas">SaaS</option>
                    <option value="finance">Finance</option>
                    <option value="healthcare">Healthcare</option>
                    <option value="real_estate">Real Estate</option>
                    <option value="other">Other</option>
                  </select>
                </div>
              </div>
              <div className="flex justify-between">
                <button
                  onClick={() => setStep(2)}
                  className="px-6 py-3 border-2 border-border rounded-lg font-medium hover:bg-slate-50 transition-colors"
                >
                  Back
                </button>
                <button
                  onClick={() => setStep(4)}
                  disabled={!data.team_size || !data.industry}
                  className="px-6 py-3 bg-primary text-white rounded-lg font-semibold hover:bg-primary/90 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Continue
                </button>
              </div>
            </div>
          )}

          {step === 4 && (
            <div className="text-center">
              <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
                <CheckCircle className="w-10 h-10 text-green-600" />
              </div>
              <h2 className="text-4xl font-bold text-foreground mb-4">You're All Set!</h2>
              <p className="text-lg text-secondary mb-8">
                Your workspace is ready. Let's start generating leads and closing deals!
              </p>
              <button
                onClick={handleComplete}
                className="px-8 py-4 bg-primary text-white rounded-lg font-semibold hover:bg-primary/90 transition-all duration-200 inline-flex items-center gap-2"
              >
                Go to Dashboard
                <ChevronRight className="w-5 h-5" />
              </button>
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
};

export default OnboardingWizard;