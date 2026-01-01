import React from 'react';
import DashboardLayout from '@/components/DashboardLayout';
import { Mail } from 'lucide-react';

const SequencesPage = () => {
  return (
    <DashboardLayout>
      <div>
        <h1 className="text-4xl font-bold text-foreground mb-2">Email Sequences</h1>
        <p className="text-secondary mb-8">Create automated email campaigns</p>
        <div className="bg-white p-12 rounded-xl border border-border text-center">
          <Mail className="w-16 h-16 text-secondary mx-auto mb-4" />
          <p className="text-lg text-secondary">Email sequences feature coming soon</p>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default SequencesPage;