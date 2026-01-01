import React from 'react';
import Sidebar from '@/components/Sidebar';
import AICoach from '@/components/AICoach';
import AICopilot from '@/components/AICopilot';

const DashboardLayout = ({ children }) => {
  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      <div className="ml-64">
        <main className="p-8">
          {children}
        </main>
      </div>
      <AICoach />
      <AICopilot />
    </div>
  );
};

export default DashboardLayout;