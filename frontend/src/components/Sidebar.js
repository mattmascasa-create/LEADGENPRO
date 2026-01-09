import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import PhoneDialer from './PhoneDialer';
import NotificationCenter from './NotificationCenter';
import { 
  LayoutDashboard, 
  GitBranch, 
  Users, 
  Calendar, 
  Mail, 
  FileText, 
  BarChart3, 
  Settings,
  LogOut,
  Sparkles,
  Phone,
  UserCog,
  CheckSquare,
  FolderOpen,
  CalendarDays,
  Mic,
  PhoneCall,
  HardDrive,
  Wand2,
  PieChart,
  Shield,
  Link2,
  Menu,
  X,
  AlertTriangle,
  CalendarClock,
  TrendingUp,
  MailCheck
} from 'lucide-react';

// Admin emails that always have admin access
const ADMIN_EMAILS = ['mattmascasa@gmail.com', 'monika.iordanoff@gmail.com', 'admin@test.com'];

// Helper to check if user is admin
const isAdminUser = (user) => {
  return user?.role === 'admin' || ADMIN_EMAILS.includes(user?.email);
};

const Sidebar = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [showDialer, setShowDialer] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  
  const isAdmin = isAdminUser(user);

  // Check if mobile on mount and resize
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 1024);
      if (window.innerWidth >= 1024) {
        setIsMobileMenuOpen(false);
      }
    };
    
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Close mobile menu on route change
  useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [location.pathname]);

  // Admin navigation - full access
  const adminNavigation = [
    { name: 'Dashboard', href: '/dashboard', icon: Shield },
    { name: 'Calendar', href: '/calendar', icon: CalendarDays },
    { name: 'Scheduling', href: '/scheduling', icon: CalendarClock },
    { name: 'Call Lists', href: '/call-lists', icon: Phone },
    { name: 'Call Analytics', href: '/call-analytics', icon: Mic },
    { name: 'AI Email', href: '/ai-email', icon: Wand2 },
    { name: 'Tasks', href: '/tasks', icon: CheckSquare },
    { name: 'Meetings', href: '/meetings', icon: Calendar },
    { name: 'Pipeline', href: '/pipeline', icon: GitBranch },
    { name: 'All Leads', href: '/leads', icon: Users },
    { name: 'Content Hub', href: '/content-hub', icon: HardDrive },
    { name: 'Sequences', href: '/sequences', icon: Mail },
    { name: 'Templates', href: '/templates', icon: FileText },
    { name: 'Analytics', href: '/analytics', icon: BarChart3 },
    { name: 'Reports', href: '/reports', icon: PieChart },
    { name: 'CRM', href: '/integrations', icon: Link2 },
    { name: 'Settings', href: '/settings', icon: Settings },
    { name: 'Users', href: '/admin/users', icon: UserCog },
    { name: 'Distribute', href: '/admin/distribute', icon: FolderOpen },
    { name: 'System Errors', href: '/admin/errors', icon: AlertTriangle },
  ];

  // Employee navigation - limited access
  const employeeNavigation = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'My Leads', href: '/call-lists', icon: Phone },
    { name: 'Calendar', href: '/calendar', icon: CalendarDays },
    { name: 'Scheduling', href: '/scheduling', icon: CalendarClock },
    { name: 'Tasks', href: '/tasks', icon: CheckSquare },
    { name: 'Meetings', href: '/meetings', icon: Calendar },
    { name: 'Call Analytics', href: '/call-analytics', icon: Mic },
    { name: 'Settings', href: '/settings', icon: Settings },
  ];

  const navigation = isAdmin ? adminNavigation : employeeNavigation;

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  // Mobile hamburger button (fixed position)
  const MobileMenuButton = () => (
    <button
      onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
      className="lg:hidden fixed top-4 left-4 z-[60] p-2 bg-slate-900 rounded-lg shadow-lg"
      aria-label="Toggle menu"
    >
      {isMobileMenuOpen ? (
        <X className="w-6 h-6 text-white" />
      ) : (
        <Menu className="w-6 h-6 text-white" />
      )}
    </button>
  );

  // Overlay for mobile
  const MobileOverlay = () => (
    <div
      className={`lg:hidden fixed inset-0 bg-black/50 z-40 transition-opacity duration-300 ${
        isMobileMenuOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
      }`}
      onClick={() => setIsMobileMenuOpen(false)}
    />
  );

  return (
    <>
      <MobileMenuButton />
      <MobileOverlay />
      
      {/* Sidebar */}
      <div className={`
        sidebar-dark h-screen fixed left-0 top-0 flex flex-col z-50
        transition-transform duration-300 ease-in-out
        w-64 lg:w-64
        ${isMobile ? (isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full') : 'translate-x-0'}
      `}>
        {/* Logo */}
        <div className="p-4 lg:p-6 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-primary rounded-md flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <span className="text-lg lg:text-xl font-black text-white">LeadGen Pro</span>
          </div>
        </div>

        {/* Role Badge & Notifications */}
        <div className="px-3 lg:px-4 pt-3 lg:pt-4 flex items-center gap-2">
          <div className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-xs lg:text-sm font-medium ${
            isAdmin ? 'bg-red-500/20 text-red-400' : 'bg-blue-500/20 text-blue-400'
          }`}>
            {isAdmin ? <Shield className="w-4 h-4" /> : <Users className="w-4 h-4" />}
            {isAdmin ? 'Admin' : 'Employee'}
          </div>
          {isAdmin && (
            <div className="bg-slate-800 rounded-lg">
              <NotificationCenter />
            </div>
          )}
        </div>

        {/* Quick Call Button */}
        <div className="px-3 lg:px-4 pt-3 lg:pt-4">
          <button
            onClick={() => setShowDialer(true)}
            className="w-full flex items-center justify-center gap-2 px-3 lg:px-4 py-2.5 lg:py-3 bg-green-500 hover:bg-green-600 text-white rounded-xl font-medium transition-all shadow-lg shadow-green-500/20 text-sm lg:text-base"
            data-testid="quick-call-btn"
          >
            <PhoneCall className="w-4 h-4 lg:w-5 lg:h-5" />
            <span>Quick Call</span>
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-3 lg:p-4 space-y-1 overflow-y-auto">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href;
            const Icon = item.icon;
            
            return (
              <Link
                key={item.name}
                to={item.href}
                className={`
                  flex items-center gap-3 px-3 lg:px-4 py-2.5 lg:py-3 rounded-lg transition-all duration-200 text-sm lg:text-base
                  ${isActive 
                    ? 'bg-primary text-white shadow-lg' 
                    : 'text-slate-400 hover:text-white hover:bg-slate-800'
                  }
                `}
              >
                <Icon className="w-4 h-4 lg:w-5 lg:h-5 flex-shrink-0" />
                <span className="font-medium truncate">{item.name}</span>
              </Link>
            );
          })}
        </nav>

        {/* User Section */}
        <div className="p-3 lg:p-4 border-t border-slate-800">
          <div className="flex items-center gap-3 mb-3 lg:mb-4">
            <div className="w-8 h-8 lg:w-10 lg:h-10 bg-gradient-to-br from-primary to-accent rounded-full flex items-center justify-center text-white font-semibold text-sm lg:text-base flex-shrink-0">
              {user?.full_name?.charAt(0) || 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs lg:text-sm font-medium text-white truncate">{user?.full_name}</p>
              <p className="text-xs text-slate-400 capitalize">{isAdmin ? 'Admin' : user?.role}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-2 px-3 lg:px-4 py-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-all duration-200 text-sm"
          >
            <LogOut className="w-4 h-4" />
            <span>Sign Out</span>
          </button>
        </div>

        {/* Phone Dialer Modal */}
        <PhoneDialer 
          isOpen={showDialer} 
          onClose={() => setShowDialer(false)} 
        />
      </div>
    </>
  );
};

export default Sidebar;
