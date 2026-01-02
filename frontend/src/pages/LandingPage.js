import React from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Sparkles, BarChart3, Zap, Calendar, Phone, Brain, CheckCircle, ArrowRight, Users } from 'lucide-react';

const LandingPage = () => {
  const features = [
    {
      icon: <Phone className="w-8 h-8" />,
      title: 'Click-to-Call',
      description: 'Make calls directly from the platform with Twilio VoIP integration and call logging'
    },
    {
      icon: <Calendar className="w-8 h-8" />,
      title: 'Team Calendar',
      description: 'Schedule meetings and appointments visible to the entire team'
    },
    {
      icon: <BarChart3 className="w-8 h-8" />,
      title: 'Call Analytics',
      description: 'Track call outcomes, duration, and get AI-powered coaching insights'
    },
    {
      icon: <Users className="w-8 h-8" />,
      title: 'Lead Management',
      description: 'Manage your sales pipeline with drag-and-drop Kanban boards'
    },
    {
      icon: <Brain className="w-8 h-8" />,
      title: 'AI Assistant',
      description: 'Get guidance and help navigating the platform with our AI copilot'
    },
    {
      icon: <Zap className="w-8 h-8" />,
      title: 'Task Management',
      description: 'Create and assign tasks, track follow-ups, and stay organized'
    }
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-white/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-primary rounded-md flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-black text-foreground">LeadGen Pro</span>
          </div>
          <div className="flex items-center gap-4">
            <Link to="/login" className="text-sm font-medium text-secondary hover:text-foreground transition-colors">
              Sign In
            </Link>
            <Link to="/register" className="px-4 py-2 bg-primary text-white rounded-md font-medium hover:bg-primary/90 transition-colors">
              Get Started
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="py-24 px-6">
        <div className="max-w-7xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-orange-50 border border-orange-200 rounded-full text-sm font-medium text-orange-600 mb-6">
              <Sparkles className="w-4 h-4" />
              Internal Sales Platform
            </div>
            <h1 className="text-5xl md:text-7xl font-bold tracking-tight text-foreground mb-6">
              Your Team's
              <br />
              <span className="bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
                Sales Command Center
              </span>
            </h1>
            <p className="text-xl text-secondary max-w-3xl mx-auto mb-12">
              Make calls, schedule meetings, manage leads, and track your team's performance — 
              all in one powerful platform built for your sales team.
            </p>
            <div className="flex gap-4 justify-center flex-wrap">
              <Link to="/login">
                <button className="px-8 py-4 bg-primary text-white rounded-lg font-semibold text-lg hover:bg-primary/90 transition-all duration-200 shadow-lg hover:shadow-xl flex items-center gap-2">
                  Sign In to Dashboard
                  <ArrowRight className="w-5 h-5" />
                </button>
              </Link>
              <Link to="/register">
                <button className="px-8 py-4 border-2 border-border text-foreground rounded-lg font-semibold text-lg hover:bg-slate-50 transition-all duration-200">
                  Create Account
                </button>
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-24 px-6 bg-slate-50">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-foreground mb-4">Everything Your Team Needs</h2>
            <p className="text-lg text-secondary">Powerful tools to streamline your sales process</p>
          </div>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                viewport={{ once: true }}
                className="bg-white p-8 rounded-xl border border-border hover:border-primary transition-all duration-300 hover:shadow-lg group"
              >
                <div className="w-16 h-16 bg-primary/10 rounded-lg flex items-center justify-center text-primary mb-6 group-hover:scale-110 transition-transform duration-300">
                  {feature.icon}
                </div>
                <h3 className="text-xl font-semibold text-foreground mb-3">{feature.title}</h3>
                <p className="text-secondary">{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Quick Access */}
      <section className="py-24 px-6">
        <div className="max-w-5xl mx-auto text-center">
          <h2 className="text-4xl font-bold text-foreground mb-12">Quick Access</h2>
          <div className="grid md:grid-cols-3 gap-8">
            {[
              { icon: <Phone className="w-8 h-8" />, label: 'Make Calls', desc: 'Click-to-call with VoIP' },
              { icon: <Calendar className="w-8 h-8" />, label: 'Schedule Meetings', desc: 'Team calendar & booking' },
              { icon: <Users className="w-8 h-8" />, label: 'Manage Pipeline', desc: 'Track leads & deals' }
            ].map((item, index) => (
              <div key={index} className="bg-white p-8 rounded-xl border border-border">
                <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center text-primary mx-auto mb-4">
                  {item.icon}
                </div>
                <div className="text-xl font-semibold text-foreground mb-2">{item.label}</div>
                <div className="text-secondary">{item.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-24 px-6 bg-primary">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-5xl font-bold text-white mb-6">Ready to Get Started?</h2>
          <p className="text-xl text-primary-foreground/80 mb-12">
            Sign in to access your sales dashboard and start making calls today.
          </p>
          <Link to="/login">
            <button className="px-10 py-5 bg-white text-primary rounded-lg font-bold text-xl hover:bg-slate-50 transition-all duration-200 shadow-2xl">
              Go to Dashboard
            </button>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border py-12 px-6 bg-white">
        <div className="max-w-7xl mx-auto text-center text-secondary">
          <p>&copy; 2025 LeadGen Pro. Internal Sales Platform.</p>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;