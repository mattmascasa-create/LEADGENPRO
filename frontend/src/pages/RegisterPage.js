import React from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Zap, ShieldAlert, ArrowLeft } from 'lucide-react';

const RegisterPage = () => {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4 py-12">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md"
      >
        <div className="glassmorphism p-8 rounded-2xl text-center">
          <div className="inline-flex items-center gap-2 mb-6">
            <Zap className="w-10 h-10 text-primary" />
            <h1 className="text-3xl font-black text-primary">LeadGen Pro</h1>
          </div>
          
          <div className="w-16 h-16 bg-amber-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <ShieldAlert className="w-8 h-8 text-amber-600" />
          </div>
          
          <h2 className="text-xl font-bold text-foreground mb-3">
            Account Creation Restricted
          </h2>
          
          <p className="text-muted-foreground mb-6">
            New accounts can only be created by administrators. 
            If you need access, please contact your administrator.
          </p>
          
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Already have an account created by an admin?
            </p>
            
            <Link 
              to="/login"
              className="w-full py-3 bg-primary text-primary-foreground rounded-lg font-bold text-lg transition-all duration-300 hover:scale-105 glow-effect flex items-center justify-center gap-2"
            >
              Sign In with Google
            </Link>
            
            <Link 
              to="/"
              className="flex items-center justify-center gap-2 text-muted-foreground hover:text-primary transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to home
            </Link>
          </div>
        </div>
      </motion.div>
    </div>
  );
};

export default RegisterPage;
