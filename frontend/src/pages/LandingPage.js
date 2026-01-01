import React from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Zap, Target, TrendingUp, Users, Award, BarChart3 } from 'lucide-react';

const LandingPage = () => {
  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Hero Section */}
      <div 
        className="relative min-h-screen flex items-center justify-center overflow-hidden"
        style={{
          backgroundImage: `url('https://images.unsplash.com/photo-1762279388988-3f8abcc7dca2?crop=entropy&cs=srgb&fm=jpg&q=85')`,
          backgroundSize: 'cover',
          backgroundPosition: 'center'
        }}
      >
        <div className="absolute inset-0 bg-black/70" />
        
        <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-12 text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            <h1 className="text-6xl lg:text-8xl font-black mb-6 bg-gradient-to-r from-primary via-accent to-primary bg-clip-text text-transparent">
              LeadGen Pro
            </h1>
            <p className="text-xl lg:text-3xl mb-8 text-muted-foreground max-w-3xl mx-auto">
              AI-Powered Lead Generation & Sales Automation Platform
            </p>
            <p className="text-lg mb-12 text-muted-foreground max-w-2xl mx-auto">
              Supercharge your sales team with intelligent lead management, automated workflows, and gamified performance tracking
            </p>
            
            <div className="flex gap-6 justify-center flex-wrap">
              <Link to="/register">
                <button className="px-8 py-4 bg-primary text-primary-foreground rounded-lg font-bold text-lg transition-all duration-300 hover:scale-105 glow-effect">
                  Get Started Free
                </button>
              </Link>
              <Link to="/login">
                <button className="px-8 py-4 border-2 border-primary text-primary rounded-lg font-bold text-lg transition-all duration-300 hover:bg-primary/10">
                  Sign In
                </button>
              </Link>
            </div>
          </motion.div>
        </div>
      </div>

      {/* Features Section */}
      <div className="py-24 px-4 sm:px-6 lg:px-12">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            transition={{ duration: 0.8 }}
            className="text-center mb-16"
          >
            <h2 className="text-5xl font-black mb-6 text-primary">Powerful Features</h2>
            <p className="text-xl text-muted-foreground">Everything you need to dominate your market</p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {[
              {
                icon: <Zap className="w-12 h-12" />,
                title: 'AI-Powered Lead Scoring',
                description: 'Automatically prioritize your hottest leads with machine learning'
              },
              {
                icon: <Target className="w-12 h-12" />,
                title: 'Smart Assignment',
                description: 'Intelligently distribute leads to the right team members'
              },
              {
                icon: <TrendingUp className="w-12 h-12" />,
                title: 'Performance Analytics',
                description: 'Track conversion rates, revenue, and team performance in real-time'
              },
              {
                icon: <Users className="w-12 h-12" />,
                title: 'Team Collaboration',
                description: 'Seamless communication and task management for your sales team'
              },
              {
                icon: <Award className="w-12 h-12" />,
                title: 'Gamification',
                description: 'Motivate your team with leaderboards, badges, and rewards'
              },
              {
                icon: <BarChart3 className="w-12 h-12" />,
                title: 'Revenue Tracking',
                description: 'Monitor commissions, bonuses, and ROI with precision'
              }
            ].map((feature, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1, duration: 0.5 }}
                className="glassmorphism p-8 rounded-lg hover:border-primary transition-all duration-300 group"
              >
                <div className="text-primary mb-4 group-hover:scale-110 transition-transform duration-300">
                  {feature.icon}
                </div>
                <h3 className="text-2xl font-bold mb-3">{feature.title}</h3>
                <p className="text-muted-foreground">{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </div>

      {/* CTA Section */}
      <div className="py-24 px-4 sm:px-6 lg:px-12">
        <div className="max-w-4xl mx-auto text-center glassmorphism p-12 rounded-2xl">
          <h2 className="text-5xl font-black mb-6">Ready to Dominate?</h2>
          <p className="text-xl text-muted-foreground mb-8">
            Join thousands of sales teams crushing their targets with LeadGen Pro
          </p>
          <Link to="/register">
            <button className="px-10 py-5 bg-accent text-accent-foreground rounded-lg font-bold text-xl transition-all duration-300 hover:scale-105 glow-effect">
              Start Free Trial
            </button>
          </Link>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t border-border py-8 px-4 sm:px-6 lg:px-12">
        <div className="max-w-7xl mx-auto text-center text-muted-foreground">
          <p>&copy; 2025 LeadGen Pro. Built with Emergent AI.</p>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;