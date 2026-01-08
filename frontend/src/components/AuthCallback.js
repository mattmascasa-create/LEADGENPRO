import React, { useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { toast } from 'react-toastify';
import axios from 'axios';
import { Loader2 } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH

const AuthCallback = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { setUser } = useAuth();
  const hasProcessed = useRef(false);

  useEffect(() => {
    // Prevent double processing in StrictMode
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const processGoogleAuth = async () => {
      try {
        // Extract session_id from URL fragment
        const hash = location.hash;
        const sessionIdMatch = hash.match(/session_id=([^&]+)/);
        
        if (!sessionIdMatch) {
          toast.error('Invalid authentication response');
          navigate('/login');
          return;
        }

        const sessionId = sessionIdMatch[1];

        // Send session_id to backend
        const response = await axios.post(`${API_URL}/api/auth/google`, {
          session_id: sessionId
        });

        if (response.data.access_token && response.data.user) {
          // Store token and user data
          localStorage.setItem('token', response.data.access_token);
          
          // Update auth context
          setUser(response.data.user);
          
          // Set axios default header
          axios.defaults.headers.common['Authorization'] = `Bearer ${response.data.access_token}`;
          
          toast.success('Successfully signed in with Google!');
          
          // Navigate to dashboard, passing user data to avoid auth check race condition
          navigate('/dashboard', { 
            replace: true,
            state: { user: response.data.user }
          });
        } else {
          throw new Error('Invalid response from server');
        }
      } catch (error) {
        console.error('Google auth error:', error);
        const errorMessage = error.response?.data?.detail || 'Google sign-in failed';
        toast.error(errorMessage);
        navigate('/login');
      }
    };

    processGoogleAuth();
  }, [location, navigate, setUser]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="text-center">
        <Loader2 className="w-12 h-12 text-primary animate-spin mx-auto mb-4" />
        <h2 className="text-xl font-semibold text-foreground mb-2">Signing you in...</h2>
        <p className="text-muted-foreground">Please wait while we complete the authentication.</p>
      </div>
    </div>
  );
};

export default AuthCallback;
