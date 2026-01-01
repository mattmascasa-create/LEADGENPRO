import React from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Sparkles, BarChart3, Zap, Calendar, Mail, Brain, CheckCircle, ArrowRight } from 'lucide-react';

const LandingPage = () => {
  const features = [
    {
      icon: <Brain className="w-8 h-8" />,
      title: 'AI-Powered Insights',
      description: 'Get real-time recommendations and lead scoring powered by advanced AI'
    },
    {
      icon: <Mail className="w-8 h-8" />,
      title: 'Email Automation',
      description: 'Create multi-step sequences that run on autopilot, like Outreach but better'
    },
    {
      icon: <BarChart3 className="w-8 h-8" />,
      title: 'Call Analytics',
      description: 'Record, transcribe, and analyze every sales call with AI, inspired by Gong'
    },
    {
      icon: <Calendar className="w-8 h-8" />,
      title: 'Shared Calendar',
      description: 'Let prospects book time with you automatically, no back-and-forth'
    },
    {
      icon: <Zap className="w-8 h-8" />,
      title: 'Smart Workflows',
      description: 'Automate repetitive tasks and focus on closing deals'
    },
    {
      icon: <Sparkles className="w-8 h-8" />,
      title: 'Intelligent Coaching',
      description: 'Get AI-powered coaching to improve your sales technique'
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
              AI-Powered Sales Automation
            </div>
            <h1 className="text-5xl md:text-7xl font-bold tracking-tight text-foreground mb-6">
              Close More Deals,
              <br />
              <span className="bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
                Work Less
              </span>
            </h1>
            <p className="text-xl text-secondary max-w-3xl mx-auto mb-12">
              Enterprise-grade lead generation platform with AI insights, email automation, and call analytics. 
              Built for modern sales teams who demand the best.
            </p>
            <div className="flex gap-4 justify-center flex-wrap">
              <Link to="/register">
                <button className="px-8 py-4 bg-primary text-white rounded-lg font-semibold text-lg hover:bg-primary/90 transition-all duration-200 shadow-lg hover:shadow-xl flex items-center gap-2">
                  Start Free Trial
                  <ArrowRight className="w-5 h-5" />
                </button>
              </Link>
              <button className="px-8 py-4 border-2 border-border text-foreground rounded-lg font-semibold text-lg hover:bg-slate-50 transition-all duration-200">
                Watch Demo
              </button>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-24 px-6 bg-slate-50">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-foreground mb-4">Everything You Need to Dominate</h2>
            <p className="text-lg text-secondary">Powerful features that scale with your business</p>
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

      {/* Social Proof */}
      <section className="py-24 px-6">
        <div className="max-w-5xl mx-auto text-center">
          <h2 className="text-4xl font-bold text-foreground mb-12">Trusted by High-Performing Sales Teams</h2>
          <div className="grid md:grid-cols-3 gap-12">
            {[
              { metric: '10,000+', label: 'Active Users' },
              { metric: '2.4M+', label: 'Leads Managed' },
              { metric: '95%', label: 'Customer Satisfaction' }
            ].map((stat, index) => (
              <div key={index}>
                <div className="text-5xl font-black metric-value text-primary mb-2">{stat.metric}</div>
                <div className="text-lg text-secondary">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-24 px-6 bg-primary">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-5xl font-bold text-white mb-6">Ready to Transform Your Sales Process?</h2>
          <p className="text-xl text-primary-foreground/80 mb-12">
            Join thousands of sales professionals who are closing more deals with LeadGen Pro
          </p>
          <Link to="/register">
            <button className="px-10 py-5 bg-white text-primary rounded-lg font-bold text-xl hover:bg-slate-50 transition-all duration-200 shadow-2xl">
              Get Started Free
            </button>
          </Link>
          <p className="text-sm text-primary-foreground/60 mt-6">No credit card required • 14-day free trial</p>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border py-12 px-6 bg-white">
        <div className="max-w-7xl mx-auto text-center text-secondary">
          <p>&copy; 2025 LeadGen Pro. Built with Emergent AI.</p>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;