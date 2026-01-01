import React from 'react';
import DashboardLayout from '@/components/DashboardLayout';
import { Calendar as CalendarIcon } from 'lucide-react';

const AppointmentsPage = () => {
  return (
    <DashboardLayout>
      <div>
        <h1 className="text-4xl font-bold text-foreground mb-2">Calendar & Appointments</h1>
        <p className="text-secondary mb-8">Manage your meetings and appointments</p>
        <div className="bg-white p-12 rounded-xl border border-border text-center">
          <CalendarIcon className="w-16 h-16 text-secondary mx-auto mb-4" />
          <p className="text-lg text-secondary">Calendar feature coming soon</p>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default AppointmentsPage;