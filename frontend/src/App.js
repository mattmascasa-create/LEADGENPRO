import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import '@/App.css';

// Pages
import LandingPage from '@/pages/LandingPage';
import LoginPage from '@/pages/LoginPage';
import RegisterPage from '@/pages/RegisterPage';
import OnboardingWizard from '@/pages/OnboardingWizard';
import DashboardPage from '@/pages/DashboardPage';
import AdminDashboardPage from '@/pages/AdminDashboardPage';
import EmployeeDashboardPage from '@/pages/EmployeeDashboardPage';
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
import CallAnalyticsDashboard from '@/pages/CallAnalyticsDashboard';
import AdminUsersPage from '@/pages/AdminUsersPage';
import AdminErrorsPage from '@/pages/AdminErrorsPage';
import BookingPage from '@/pages/BookingPage';
import BookingPageEnhanced from '@/pages/BookingPageEnhanced';
import SchedulingSettingsPage from '@/pages/SchedulingSettingsPage';
import ContentHubPage from '@/pages/ContentHubPage';
import AIEmailPage from '@/pages/AIEmailPage';
import AdvancedReportingPage from '@/pages/AdvancedReportingPage';
import SettingsPage from '@/pages/SettingsPage';
import CRMIntegrationsPage from '@/pages/CRMIntegrationsPage';
import EmailAnalyticsPage from '@/pages/EmailAnalyticsPage';
import PipelineForecastPage from '@/pages/PipelineForecastPage';

import TasksPage from '@/pages/TasksPage';
import MeetingsPage from '@/pages/MeetingsPage';

// Components
import AIAssistant from '@/components/AIAssistant';
import AuthCallback from '@/components/AuthCallback';
import SupportBot from '@/components/SupportBot';
import ErrorBoundary from '@/components/ErrorBoundary';

// Auth Context
import { AuthProvider, useAuth } from '@/context/AuthContext';

// Admin emails that always have admin access
const ADMIN_EMAILS = ['mattmascasa@gmail.com', 'monika.iordanoff@gmail.com', 'admin@test.com'];

// Helper to check if user is admin
const isAdminUser = (user) => {
  return user?.role === 'admin' || ADMIN_EMAILS.includes(user?.email);
};

const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();
  const location = useLocation();
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-primary text-xl">Loading...</div>
      </div>
    );
  }
  
  // If we have user data from state (passed from AuthCallback), use it
  if (location.state?.user) {
    return children;
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

// Admin-only route wrapper
const AdminRoute = ({ children }) => {
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
  
  if (!isAdminUser(user)) {
    return <Navigate to="/employee-dashboard" replace />;
  }
  
  return children;
};

// Smart Dashboard Router - routes to admin or employee dashboard based on role
const SmartDashboard = () => {
  const { user } = useAuth();
  
  if (isAdminUser(user)) {
    return <AdminDashboardPage />;
  }
  
  return <EmployeeDashboardPage />;
};

// Router wrapper that detects Google OAuth session_id in URL fragment
// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
const AppRouter = () => {
  const location = useLocation();
  
  // Check URL fragment (not query params) for session_id - SYNCHRONOUSLY during render
  // This prevents race conditions by processing new session_id FIRST before checking existing session_token
  if (location.hash?.includes('session_id=')) {
    return <AuthCallback />;
  }
  
  return (
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
            <SmartDashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin-dashboard"
        element={
          <AdminRoute>
            <AdminDashboardPage />
          </AdminRoute>
        }
      />
      <Route
        path="/admin/errors"
        element={
          <AdminRoute>
            <AdminErrorsPage />
          </AdminRoute>
        }
      />
      <Route
        path="/employee-dashboard"
        element={
          <ProtectedRoute>
            <EmployeeDashboardPage />
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
          <AdminRoute>
            <AdminDistributePage />
          </AdminRoute>
        }
      />
      <Route
        path="/admin/users"
        element={
          <AdminRoute>
            <AdminUsersPage />
          </AdminRoute>
        }
      />
      <Route
        path="/integrations"
        element={
          <AdminRoute>
            <CRMIntegrationsPage />
          </AdminRoute>
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
            <CallAnalyticsDashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/book/:userId"
        element={<BookingPageEnhanced />}
      />
      <Route
        path="/scheduling"
        element={
          <ProtectedRoute>
            <SchedulingSettingsPage />
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
      <Route
        path="/ai-email"
        element={
          <ProtectedRoute>
            <AIEmailPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/reports"
        element={
          <ProtectedRoute>
            <AdvancedReportingPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/email-analytics"
        element={
          <ProtectedRoute>
            <EmailAnalyticsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/forecasting"
        element={
          <ProtectedRoute>
            <PipelineForecastPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/settings"
        element={
          <ProtectedRoute>
            <SettingsPage />
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
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

function AppContent() {
  return (
    <ErrorBoundary>
      <div className="App">
        <BrowserRouter>
          <AppRouter />
          <AIAssistant />
          <SupportBot />
          <ToastContainer 
            position="top-right"
            autoClose={3000}
            hideProgressBar={false}
            newestOnTop
            closeOnClick
            rtl={false}
            pauseOnFocusLoss
            draggable
            pauseOnHover
            theme="light"
          />
        </BrowserRouter>
      </div>
    </ErrorBoundary>
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