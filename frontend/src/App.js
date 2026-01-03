import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import '@/App.css';

// Pages
import LandingPage from '@/pages/LandingPage';
import LoginPage from '@/pages/LoginPage';
import RegisterPage from '@/pages/RegisterPage';
import OnboardingWizard from '@/pages/OnboardingWizard';
import DashboardPage from '@/pages/DashboardPage';
import PipelinePage from '@/pages/PipelinePage';
import LeadsPage from '@/pages/LeadsPage';
import LeadDetailPage from '@/pages/LeadDetailPage';
import AppointmentsPage from '@/pages/AppointmentsPage';
import SequencesPage from '@/pages/SequencesPage';
import TemplatesPage from '@/pages/TemplatesPage';
import AnalyticsPage from '@/pages/AnalyticsPage';
import AdminDistributePage from '@/pages/AdminDistributePage';
import CallListsPage from '@/pages/CallListsPage';
import CalendarPage from '@/pages/CalendarPage';
import CallAnalyticsPage from '@/pages/CallAnalyticsPage';
import AdminUsersPage from '@/pages/AdminUsersPage';
import BookingPage from '@/pages/BookingPage';
import ContentHubPage from '@/pages/ContentHubPage';
import AIEmailPage from '@/pages/AIEmailPage';

import TasksPage from '@/pages/TasksPage';
import MeetingsPage from '@/pages/MeetingsPage';

// Components
import AIAssistant from '@/components/AIAssistant';

// Auth Context
import { AuthProvider, useAuth } from '@/context/AuthContext';

const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-primary text-xl">Loading...</div>
      </div>
    );
  }
  
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  
  // Redirect to onboarding if not completed
  if (!user.onboarding_completed && window.location.pathname !== '/onboarding') {
    return <Navigate to="/onboarding" replace />;
  }
  
  return children;
};

function AppContent() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route
            path="/onboarding"
            element={
              <ProtectedRoute>
                <OnboardingWizard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/pipeline"
            element={
              <ProtectedRoute>
                <PipelinePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/leads"
            element={
              <ProtectedRoute>
                <LeadsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/leads/:id"
            element={
              <ProtectedRoute>
                <LeadDetailPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/appointments"
            element={
              <ProtectedRoute>
                <AppointmentsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/sequences"
            element={
              <ProtectedRoute>
                <SequencesPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/templates"
            element={
              <ProtectedRoute>
                <TemplatesPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/analytics"
            element={
              <ProtectedRoute>
                <AnalyticsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/distribute"
            element={
              <ProtectedRoute>
                <AdminDistributePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/tasks"
            element={
              <ProtectedRoute>
                <TasksPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/meetings"
            element={
              <ProtectedRoute>
                <MeetingsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/call-lists"
            element={
              <ProtectedRoute>
                <CallListsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/calendar"
            element={
              <ProtectedRoute>
                <CalendarPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/call-analytics"
            element={
              <ProtectedRoute>
                <CallAnalyticsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/users"
            element={
              <ProtectedRoute>
                <AdminUsersPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/content-hub"
            element={
              <ProtectedRoute>
                <ContentHubPage />
              </ProtectedRoute>
            }
          />
          {/* Public booking page - no auth required */}
          <Route path="/book/:userId" element={<BookingPage />} />
        </Routes>
        {/* AI Assistant Widget - Available on all pages */}
        <AIAssistant />
      </BrowserRouter>
      <ToastContainer
        position="top-right"
        theme="light"
        toastStyle={{
          background: '#ffffff',
          border: '1px solid hsl(214 32% 91%)',
          color: 'hsl(222 47% 11%)'
        }}
      />
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;