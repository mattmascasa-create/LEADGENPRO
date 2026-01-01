import React from 'react';
import DashboardLayout from '@/components/DashboardLayout';
import { FileText } from 'lucide-react';

const TemplatesPage = () => {
  return (
    <DashboardLayout>
      <div>
        <h1 className="text-4xl font-bold text-foreground mb-2">Templates</h1>
        <p className="text-secondary mb-8">Manage your email and SMS templates</p>
        <div className="bg-white p-12 rounded-xl border border-border text-center">
          <FileText className="w-16 h-16 text-secondary mx-auto mb-4" />
          <p className="text-lg text-secondary">Templates library coming soon</p>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default TemplatesPage;