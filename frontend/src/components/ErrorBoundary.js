import React, { Component } from 'react';
import { AlertTriangle, RefreshCw, MessageCircle } from 'lucide-react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL;

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { 
      hasError: false, 
      error: null, 
      errorInfo: null,
      reportedError: null,
      isReporting: false
    };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo });
    this.reportError(error, errorInfo);
  }

  async reportError(error, errorInfo) {
    this.setState({ isReporting: true });
    
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        console.error('No token available to report error');
        return;
      }

      const response = await axios.post(
        `${API_URL}/api/errors/report`,
        {
          error_type: error.name || 'React Error',
          error_message: error.message,
          stack_trace: errorInfo?.componentStack || error.stack,
          endpoint: window.location.pathname,
          page_url: window.location.href,
          user_agent: navigator.userAgent
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      this.setState({ 
        reportedError: response.data,
        isReporting: false 
      });

    } catch (err) {
      console.error('Failed to report error:', err);
      this.setState({ isReporting: false });
    }
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null, errorInfo: null, reportedError: null });
  };

  handleOpenSupport = () => {
    // Dispatch event to open support bot with this error
    window.dispatchEvent(new CustomEvent('openSupportBot', { 
      detail: this.state.reportedError 
    }));
  };

  render() {
    if (this.state.hasError) {
      const { error, reportedError, isReporting } = this.state;

      return (
        <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
          <div className="max-w-md w-full bg-white rounded-2xl shadow-xl border border-border p-8">
            <div className="flex items-center justify-center w-16 h-16 bg-red-100 rounded-full mx-auto mb-6">
              <AlertTriangle className="w-8 h-8 text-red-500" />
            </div>
            
            <h1 className="text-2xl font-bold text-center text-foreground mb-2">
              Something went wrong
            </h1>
            
            <p className="text-secondary text-center mb-6">
              {error?.message || 'An unexpected error occurred'}
            </p>

            {reportedError && (
              <div className="bg-slate-50 rounded-lg p-4 mb-6">
                <p className="text-sm text-secondary mb-2">
                  <strong>Error ID:</strong> {reportedError.error_id}
                </p>
                <p className="text-sm text-secondary mb-2">
                  <strong>Category:</strong> {reportedError.category}
                </p>
                {reportedError.user_suggestion && (
                  <p className="text-sm text-primary">
                    <strong>Suggestion:</strong> {reportedError.user_suggestion}
                  </p>
                )}
                {reportedError.auto_fix?.success && (
                  <div className="mt-2 flex items-center gap-2 text-green-600 text-sm">
                    <span className="w-2 h-2 bg-green-500 rounded-full" />
                    Auto-fix applied: {reportedError.auto_fix.action_taken}
                  </div>
                )}
              </div>
            )}

            {isReporting && (
              <div className="flex items-center justify-center gap-2 text-secondary text-sm mb-6">
                <RefreshCw className="w-4 h-4 animate-spin" />
                Reporting error...
              </div>
            )}

            <div className="flex flex-col gap-3">
              <button
                onClick={this.handleRetry}
                className="w-full py-3 bg-primary text-white rounded-lg font-medium hover:bg-primary/90 flex items-center justify-center gap-2"
              >
                <RefreshCw className="w-5 h-5" />
                Try Again
              </button>
              
              <button
                onClick={this.handleOpenSupport}
                className="w-full py-3 bg-slate-100 text-foreground rounded-lg font-medium hover:bg-slate-200 flex items-center justify-center gap-2"
              >
                <MessageCircle className="w-5 h-5" />
                Get Help from AI Support
              </button>
              
              <button
                onClick={() => window.location.href = '/dashboard'}
                className="w-full py-2 text-secondary hover:text-foreground text-sm"
              >
                Return to Dashboard
              </button>
            </div>

            <p className="text-xs text-secondary text-center mt-6">
              Error has been automatically reported. Our team will look into it.
            </p>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
