import React from 'react';
import DashboardLayout from '@/components/DashboardLayout';
import { BarChart3 } from 'lucide-react';

const AnalyticsPage = () => {
  return (
    <DashboardLayout>
      <div>
        <h1 className="text-4xl font-bold text-foreground mb-2">Analytics & Reports</h1>
        <p className="text-secondary mb-8">Track your performance metrics</p>
        <div className="bg-white p-12 rounded-xl border border-border text-center">
          <BarChart3 className="w-16 h-16 text-secondary mx-auto mb-4" />
          <p className="text-lg text-secondary">Advanced analytics coming soon</p>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default AnalyticsPage;