import React from 'react';
import Sidebar from '@/components/Sidebar';

const DashboardLayout = ({ children }) => {
  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      <div className="ml-64">
        <main className="p-8">
          {children}
        </main>
      </div>
    </div>
  );
};

export default DashboardLayout;