import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
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
  Mic
} from 'lucide-react';

const Sidebar = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Calendar', href: '/calendar', icon: CalendarDays },
    { name: 'Call Lists', href: '/call-lists', icon: Phone, roles: ['employee', 'admin'] },
    { name: 'Call Analytics', href: '/call-analytics', icon: Mic },
    { name: 'Tasks', href: '/tasks', icon: CheckSquare },
    { name: 'Meetings', href: '/meetings', icon: Calendar },
    { name: 'Pipeline', href: '/pipeline', icon: GitBranch },
    { name: 'Leads', href: '/leads', icon: Users },
    { name: 'Sequences', href: '/sequences', icon: Mail },
    { name: 'Templates', href: '/templates', icon: FileText },
    { name: 'Analytics', href: '/analytics', icon: BarChart3 },
    { name: 'User Management', href: '/admin/users', icon: UserCog, roles: ['admin'] },
    { name: 'Distribute Leads', href: '/admin/distribute', icon: FolderOpen, roles: ['admin'] },
  ];

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const filteredNavigation = navigation.filter(item => {
    if (!item.roles) return true;
    return item.roles.includes(user?.role);
  });

  return (
    <div className="sidebar-dark h-screen w-64 fixed left-0 top-0 flex flex-col z-50">
      {/* Logo */}
      <div className="p-6 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-primary rounded-md flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <span className="text-xl font-black text-white">LeadGen Pro</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        {filteredNavigation.map((item) => {
          const isActive = location.pathname === item.href;
          const Icon = item.icon;
          
          return (
            <Link
              key={item.name}
              to={item.href}
              className={`
                flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200
                ${isActive 
                  ? 'bg-primary text-white shadow-lg' 
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'
                }
              `}
            >\n              <Icon className="w-5 h-5" />
              <span className="font-medium">{item.name}</span>
            </Link>
          );
        })}
      </nav>

      {/* User Section */}
      <div className="p-4 border-t border-slate-800">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-gradient-to-br from-primary to-accent rounded-full flex items-center justify-center text-white font-semibold">
            {user?.full_name?.charAt(0) || 'U'}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate">{user?.full_name}</p>
            <p className="text-xs text-slate-400 capitalize">{user?.role}</p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-2 px-4 py-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-all duration-200"
        >
          <LogOut className="w-4 h-4" />
          <span className="text-sm">Sign Out</span>
        </button>
      </div>
    </div>
  );
};

export default Sidebar;