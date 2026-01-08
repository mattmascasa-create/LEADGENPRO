import React from 'react';
import Sidebar from '@/components/Sidebar';
import AICoach from '@/components/AICoach';
import AICopilot from '@/components/AICopilot';
import TeamChatEnhanced from '@/components/TeamChatEnhanced';

const DashboardLayout = ({ children }) => {
  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      {/* Main content - responsive margin */}
      <div className="lg:ml-64 transition-all duration-300">
        <main className="p-4 pt-16 lg:pt-8 lg:p-8">
          {children}
        </main>
      </div>
      {/* Hide floating widgets on mobile for cleaner experience */}
      <div className="hidden lg:block">
        <AICoach />
        <AICopilot />
      </div>
      <TeamChatEnhanced />
    </div>
  );
};

export default DashboardLayout;