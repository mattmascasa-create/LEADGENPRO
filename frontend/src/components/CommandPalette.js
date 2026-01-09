import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search, Command, ArrowRight, User, Users, Phone, Mail,
  Calendar, LayoutDashboard, GitBranch, CheckSquare, Settings,
  Plus, TrendingUp, BarChart3, Mic, MessageSquare, FileText,
  Clock, Star, Zap, ArrowUp, ArrowDown, CornerDownLeft,
  X, Loader2, PhoneCall, CalendarPlus, UserPlus, ListPlus
} from 'lucide-react';
import axios from 'axios';
import { toast } from 'react-toastify';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const CommandPalette = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [recentSearches, setRecentSearches] = useState([]);
  const inputRef = useRef(null);
  const navigate = useNavigate();

  // Navigation commands
  const navigationCommands = [
    { id: 'nav-dashboard', type: 'navigation', icon: LayoutDashboard, label: 'Go to Dashboard', path: '/dashboard', keywords: ['home', 'main'] },
    { id: 'nav-leads', type: 'navigation', icon: Users, label: 'Go to Leads', path: '/leads', keywords: ['contacts', 'prospects'] },
    { id: 'nav-pipeline', type: 'navigation', icon: GitBranch, label: 'Go to Pipeline', path: '/pipeline', keywords: ['deals', 'kanban'] },
    { id: 'nav-calls', type: 'navigation', icon: Mic, label: 'Go to Call Analytics', path: '/call-analytics', keywords: ['phone', 'dialer'] },
    { id: 'nav-email', type: 'navigation', icon: Mail, label: 'Go to Email Analytics', path: '/email-analytics', keywords: ['tracking', 'sequences'] },
    { id: 'nav-forecast', type: 'navigation', icon: TrendingUp, label: 'Go to Forecasting', path: '/forecasting', keywords: ['revenue', 'pipeline'] },
    { id: 'nav-calendar', type: 'navigation', icon: Calendar, label: 'Go to Calendar', path: '/calendar', keywords: ['schedule', 'meetings'] },
    { id: 'nav-tasks', type: 'navigation', icon: CheckSquare, label: 'Go to Tasks', path: '/tasks', keywords: ['todo', 'activities'] },
    { id: 'nav-reports', type: 'navigation', icon: BarChart3, label: 'Go to Reports', path: '/reports', keywords: ['analytics', 'metrics'] },
    { id: 'nav-chat', type: 'navigation', icon: MessageSquare, label: 'Go to Team Chat', path: '/dashboard', keywords: ['messages', 'slack'] },
    { id: 'nav-settings', type: 'navigation', icon: Settings, label: 'Go to Settings', path: '/settings', keywords: ['preferences', 'config'] },
  ];

  // Quick action commands
  const actionCommands = [
    { id: 'action-new-lead', type: 'action', icon: UserPlus, label: 'Create New Lead', action: 'new-lead', keywords: ['add', 'contact'] },
    { id: 'action-new-task', type: 'action', icon: ListPlus, label: 'Create New Task', action: 'new-task', keywords: ['todo', 'reminder'] },
    { id: 'action-quick-call', type: 'action', icon: PhoneCall, label: 'Open Quick Call', action: 'quick-call', keywords: ['dial', 'phone'] },
    { id: 'action-new-meeting', type: 'action', icon: CalendarPlus, label: 'Schedule Meeting', action: 'new-meeting', keywords: ['book', 'appointment'] },
    { id: 'action-compose-email', type: 'action', icon: Mail, label: 'Compose Email', action: 'compose-email', keywords: ['send', 'write'] },
  ];

  const allCommands = [...navigationCommands, ...actionCommands];

  // Keyboard shortcut to open palette
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Cmd+K or Ctrl+K to open
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen(true);
      }
      // Escape to close
      if (e.key === 'Escape' && isOpen) {
        setIsOpen(false);
        setQuery('');
        setSelectedIndex(0);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  // Focus input when opening
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  // Load recent searches from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('commandPaletteRecent');
    if (saved) {
      setRecentSearches(JSON.parse(saved));
    }
  }, []);

  // Search leads when query changes
  const searchLeads = useCallback(async (searchQuery) => {
    if (searchQuery.length < 2) return [];
    
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/api/leads`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      const leads = response.data;
      const filtered = leads.filter(lead => {
        const fullName = `${lead.first_name || ''} ${lead.last_name || ''}`.toLowerCase();
        const company = (lead.company || '').toLowerCase();
        const email = (lead.email || '').toLowerCase();
        const q = searchQuery.toLowerCase();
        return fullName.includes(q) || company.includes(q) || email.includes(q);
      }).slice(0, 5);
      
      return filtered.map(lead => ({
        id: `lead-${lead.id}`,
        type: 'lead',
        icon: User,
        label: `${lead.first_name} ${lead.last_name}`,
        sublabel: lead.company || lead.email,
        data: lead
      }));
    } catch (error) {
      console.error('Search error:', error);
      return [];
    }
  }, []);

  // Filter and search results
  useEffect(() => {
    const search = async () => {
      if (!query.trim()) {
        // Show recent + navigation when empty
        const recent = recentSearches.slice(0, 3).map(r => ({
          ...r,
          type: 'recent',
          icon: Clock
        }));
        setResults([...recent, ...navigationCommands.slice(0, 5)]);
        setSelectedIndex(0);
        return;
      }

      setLoading(true);
      const q = query.toLowerCase();

      // Filter commands
      const matchedCommands = allCommands.filter(cmd => {
        const labelMatch = cmd.label.toLowerCase().includes(q);
        const keywordMatch = cmd.keywords?.some(k => k.includes(q));
        return labelMatch || keywordMatch;
      });

      // Search leads
      const leadResults = await searchLeads(query);

      // Combine results
      const combined = [
        ...leadResults,
        ...matchedCommands
      ].slice(0, 10);

      setResults(combined);
      setSelectedIndex(0);
      setLoading(false);
    };

    const debounce = setTimeout(search, 150);
    return () => clearTimeout(debounce);
  }, [query, recentSearches, searchLeads]);

  // Handle keyboard navigation
  const handleKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(i => Math.min(i + 1, results.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(i => Math.max(i - 1, 0));
    } else if (e.key === 'Enter' && results[selectedIndex]) {
      e.preventDefault();
      executeCommand(results[selectedIndex]);
    }
  };

  // Execute selected command
  const executeCommand = (item) => {
    // Save to recent
    const newRecent = [
      { id: item.id, label: item.label, path: item.path, action: item.action },
      ...recentSearches.filter(r => r.id !== item.id)
    ].slice(0, 5);
    setRecentSearches(newRecent);
    localStorage.setItem('commandPaletteRecent', JSON.stringify(newRecent));

    // Close palette
    setIsOpen(false);
    setQuery('');
    setSelectedIndex(0);

    // Execute based on type
    if (item.type === 'navigation' || item.type === 'recent') {
      if (item.path) {
        navigate(item.path);
      }
    } else if (item.type === 'lead') {
      // Navigate to lead detail or open quick actions
      navigate(`/leads?selected=${item.data.id}`);
      toast.info(`Selected: ${item.label}`);
    } else if (item.type === 'action') {
      handleAction(item.action);
    }
  };

  // Handle quick actions
  const handleAction = (action) => {
    switch (action) {
      case 'new-lead':
        navigate('/leads?action=new');
        break;
      case 'new-task':
        navigate('/tasks?action=new');
        break;
      case 'quick-call':
        // Trigger quick call modal via custom event
        window.dispatchEvent(new CustomEvent('openQuickCall'));
        break;
      case 'new-meeting':
        navigate('/calendar?action=new');
        break;
      case 'compose-email':
        navigate('/ai-email');
        break;
      default:
        break;
    }
  };

  // Get icon color based on type
  const getIconColor = (type) => {
    switch (type) {
      case 'lead': return 'text-blue-500 bg-blue-100';
      case 'action': return 'text-green-500 bg-green-100';
      case 'navigation': return 'text-purple-500 bg-purple-100';
      case 'recent': return 'text-slate-500 bg-slate-100';
      default: return 'text-slate-500 bg-slate-100';
    }
  };

  // Get type label
  const getTypeLabel = (type) => {
    switch (type) {
      case 'lead': return 'Lead';
      case 'action': return 'Action';
      case 'navigation': return 'Navigate';
      case 'recent': return 'Recent';
      default: return '';
    }
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh] bg-black/50 backdrop-blur-sm"
        onClick={() => {
          setIsOpen(false);
          setQuery('');
        }}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: -20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: -20 }}
          transition={{ duration: 0.15 }}
          className="w-full max-w-2xl bg-white rounded-2xl shadow-2xl overflow-hidden border border-slate-200"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Search Input */}
          <div className="flex items-center gap-3 px-4 py-4 border-b border-slate-200">
            <Search className="w-5 h-5 text-slate-400" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Search leads, navigate, or take action..."
              className="flex-1 text-lg outline-none placeholder-slate-400"
              autoComplete="off"
            />
            {loading && <Loader2 className="w-5 h-5 text-slate-400 animate-spin" />}
            <div className="flex items-center gap-1 px-2 py-1 bg-slate-100 rounded text-xs text-slate-500">
              <Command className="w-3 h-3" />
              <span>K</span>
            </div>
          </div>

          {/* Results */}
          <div className="max-h-[400px] overflow-y-auto">
            {results.length === 0 && query && !loading && (
              <div className="px-4 py-8 text-center text-slate-500">
                <Search className="w-12 h-12 mx-auto mb-3 opacity-30" />
                <p>No results found for "{query}"</p>
                <p className="text-sm mt-1">Try searching for leads, pages, or actions</p>
              </div>
            )}

            {results.map((item, index) => {
              const Icon = item.icon;
              const isSelected = index === selectedIndex;
              
              return (
                <div
                  key={item.id}
                  className={`flex items-center gap-3 px-4 py-3 cursor-pointer transition-colors ${
                    isSelected ? 'bg-primary/10' : 'hover:bg-slate-50'
                  }`}
                  onClick={() => executeCommand(item)}
                  onMouseEnter={() => setSelectedIndex(index)}
                >
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${getIconColor(item.type)}`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className={`font-medium truncate ${isSelected ? 'text-primary' : 'text-foreground'}`}>
                      {item.label}
                    </p>
                    {item.sublabel && (
                      <p className="text-sm text-slate-500 truncate">{item.sublabel}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                      item.type === 'lead' ? 'bg-blue-100 text-blue-700' :
                      item.type === 'action' ? 'bg-green-100 text-green-700' :
                      item.type === 'navigation' ? 'bg-purple-100 text-purple-700' :
                      'bg-slate-100 text-slate-600'
                    }`}>
                      {getTypeLabel(item.type)}
                    </span>
                    {isSelected && (
                      <div className="flex items-center gap-1 text-xs text-slate-400">
                        <CornerDownLeft className="w-3 h-3" />
                        <span>Enter</span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Footer with keyboard hints */}
          <div className="flex items-center justify-between px-4 py-3 border-t border-slate-200 bg-slate-50 text-xs text-slate-500">
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1">
                <ArrowUp className="w-3 h-3" />
                <ArrowDown className="w-3 h-3" />
                <span>Navigate</span>
              </span>
              <span className="flex items-center gap-1">
                <CornerDownLeft className="w-3 h-3" />
                <span>Select</span>
              </span>
              <span className="flex items-center gap-1">
                <span className="px-1.5 py-0.5 bg-slate-200 rounded text-[10px]">ESC</span>
                <span>Close</span>
              </span>
            </div>
            <div className="flex items-center gap-1">
              <Zap className="w-3 h-3 text-yellow-500" />
              <span>Pro tip: Type to search leads instantly</span>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default CommandPalette;
