import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { CheckSquare, Plus, Calendar, User, Flag, Clock, Search, Filter } from 'lucide-react';
import { toast } from 'react-toastify';
import { format } from 'date-fns';
import { motion } from 'framer-motion';
import DashboardLayout from '@/components/DashboardLayout';
import { useAuth } from '@/context/AuthContext';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const TasksPage = () => {
  const { user } = useAuth();
  const [tasks, setTasks] = useState([]);
  const [leads, setLeads] = useState([]);
  const [teamMembers, setTeamMembers] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [filter, setFilter] = useState('all'); // all, today, overdue, completed
  const [searchTerm, setSearchTerm] = useState('');
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    type: 'call', // call, email, meeting, follow_up, other
    lead_id: '',
    assigned_to: '',
    due_date: '',
    priority: 'medium'
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [tasksRes, leadsRes, usersRes] = await Promise.all([
        axios.get(`${API_URL}/api/tasks`),
        axios.get(`${API_URL}/api/leads`),
        axios.get(`${API_URL}/api/users`)
      ]);
      setTasks(tasksRes.data);
      setLeads(leadsRes.data);
      setTeamMembers(usersRes.data);
    } catch (error) {
      toast.error('Failed to load tasks');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API_URL}/api/tasks`, formData);
      toast.success('Task created!');
      setShowForm(false);
      setFormData({ title: '', description: '', type: 'call', lead_id: '', assigned_to: '', due_date: '', priority: 'medium' });
      fetchData();
    } catch (error) {
      toast.error('Failed to create task');
    }
  };

  const handleComplete = async (taskId) => {
    try {
      await axios.put(`${API_URL}/api/tasks/${taskId}/complete`);
      toast.success('Task completed!');
      fetchData();
    } catch (error) {
      toast.error('Failed to complete task');
    }
  };

  const getPriorityColor = (priority) => {
    const colors = {
      high: 'text-red-600 bg-red-100',
      medium: 'text-yellow-600 bg-yellow-100',
      low: 'text-green-600 bg-green-100'
    };
    return colors[priority] || colors.medium;
  };

  const getTypeIcon = (type) => {
    const icons = {
      call: '📞',
      email: '📧',
      meeting: '🗓️',
      follow_up: '🔔',
      other: '📋'
    };
    return icons[type] || icons.other;
  };

  const filteredTasks = tasks.filter(task => {
    const matchesSearch = task.title.toLowerCase().includes(searchTerm.toLowerCase());
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const dueDate = new Date(task.due_date);
    
    if (filter === 'today') {
      return matchesSearch && dueDate.toDateString() === today.toDateString() && !task.completed;
    } else if (filter === 'overdue') {
      return matchesSearch && dueDate < today && !task.completed;
    } else if (filter === 'completed') {
      return matchesSearch && task.completed;
    }
    return matchesSearch;
  });

  const tasksByStatus = {
    todo: filteredTasks.filter(t => !t.completed && new Date(t.due_date) >= new Date()),
    overdue: filteredTasks.filter(t => !t.completed && new Date(t.due_date) < new Date()),
    completed: filteredTasks.filter(t => t.completed)
  };

  return (
    <DashboardLayout>
      <div>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6 lg:mb-8">
          <div>
            <h1 className="text-2xl lg:text-4xl font-bold text-foreground mb-1 lg:mb-2">Task Management</h1>
            <p className="text-sm lg:text-base text-secondary">Organize and track all your sales activities</p>
          </div>
          <button
            onClick={() => setShowForm(true)}
            className="px-4 lg:px-6 py-2 lg:py-3 bg-primary text-white rounded-lg font-semibold hover:bg-primary/90 transition-all duration-200 flex items-center gap-2 text-sm lg:text-base w-full sm:w-auto justify-center"
          >
            <Plus className="w-4 h-4 lg:w-5 lg:h-5" />
            New Task
          </button>
        </div>

        {/* Filters */}
        <div className="flex flex-col gap-3 lg:gap-4 mb-6 lg:mb-8">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 lg:w-5 lg:h-5 text-secondary" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search tasks..."
              className="w-full pl-9 lg:pl-10 pr-4 py-2 lg:py-3 text-sm lg:text-base border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          <div className="flex gap-2 overflow-x-auto pb-2">
            {['all', 'today', 'overdue', 'completed'].map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 lg:px-4 py-1.5 lg:py-2 rounded-lg font-medium capitalize transition-all text-sm whitespace-nowrap ${
                  filter === f ? 'bg-primary text-white' : 'border border-border hover:bg-slate-50'
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 lg:gap-4 mb-6 lg:mb-8">
          <div className="bg-white p-3 lg:p-4 rounded-lg border border-border">
            <div className="text-xl lg:text-2xl font-bold text-primary">{tasksByStatus.todo.length}</div>
            <div className="text-xs lg:text-sm text-secondary">To Do</div>
          </div>
          <div className="bg-white p-3 lg:p-4 rounded-lg border border-border">
            <div className="text-xl lg:text-2xl font-bold text-red-600">{tasksByStatus.overdue.length}</div>
            <div className="text-xs lg:text-sm text-secondary">Overdue</div>
          </div>
          <div className="bg-white p-3 lg:p-4 rounded-lg border border-border">
            <div className="text-xl lg:text-2xl font-bold text-green-600">{tasksByStatus.completed.length}</div>
            <div className="text-xs lg:text-sm text-secondary">Completed</div>
          </div>
          <div className="bg-white p-3 lg:p-4 rounded-lg border border-border">
            <div className="text-xl lg:text-2xl font-bold text-foreground">{tasks.length}</div>
            <div className="text-xs lg:text-sm text-secondary">Total Tasks</div>
          </div>
        </div>

        {/* Task Form */}
        {showForm && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white p-6 rounded-xl border border-border mb-6"
          >
            <h3 className="text-xl font-semibold mb-4">Create New Task</h3>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid md:grid-cols-2 gap-4">
                <input
                  type="text"
                  placeholder="Task Title"
                  value={formData.title}
                  onChange={(e) => setFormData({...formData, title: e.target.value})}
                  required
                  className="px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                />
                <select
                  value={formData.type}
                  onChange={(e) => setFormData({...formData, type: e.target.value})}
                  className="px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="call">📞 Call</option>
                  <option value="email">📧 Email</option>
                  <option value="meeting">🗓️ Meeting</option>
                  <option value="follow_up">🔔 Follow Up</option>
                  <option value="other">📋 Other</option>
                </select>
              </div>
              <textarea
                placeholder="Description"
                value={formData.description}
                onChange={(e) => setFormData({...formData, description: e.target.value})}
                rows={3}
                className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary resize-none"
              />
              <div className="grid md:grid-cols-3 gap-4">
                <select
                  value={formData.lead_id}
                  onChange={(e) => setFormData({...formData, lead_id: e.target.value})}
                  className="px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="">Select Lead (Optional)</option>
                  {leads.map(lead => (
                    <option key={lead.id} value={lead.id}>
                      {lead.first_name} {lead.last_name} - {lead.company}
                    </option>
                  ))}
                </select>
                <select
                  value={formData.assigned_to}
                  onChange={(e) => setFormData({...formData, assigned_to: e.target.value})}
                  required
                  className="px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="">Assign To</option>
                  {teamMembers.map(member => (
                    <option key={member.id} value={member.id}>{member.full_name}</option>
                  ))}
                </select>
                <select
                  value={formData.priority}
                  onChange={(e) => setFormData({...formData, priority: e.target.value})}
                  className="px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="low">Low Priority</option>
                  <option value="medium">Medium Priority</option>
                  <option value="high">High Priority</option>
                </select>
              </div>
              <input
                type="datetime-local"
                value={formData.due_date}
                onChange={(e) => setFormData({...formData, due_date: e.target.value})}
                required
                className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <div className="flex gap-3">
                <button type="submit" className="flex-1 py-3 bg-primary text-white rounded-lg font-semibold hover:bg-primary/90">
                  Create Task
                </button>
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="px-6 py-3 border-2 border-border rounded-lg font-semibold hover:bg-slate-50"
                >
                  Cancel
                </button>
              </div>
            </form>
          </motion.div>
        )}

        {/* Task Kanban Board */}
        <div className="grid lg:grid-cols-3 gap-6">
          {/* To Do */}
          <div>
            <h3 className="text-lg font-bold text-foreground mb-4 flex items-center gap-2">
              <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
              To Do ({tasksByStatus.todo.length})
            </h3>
            <div className="space-y-3">
              {tasksByStatus.todo.map((task, index) => (
                <motion.div
                  key={task.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className="bg-white p-4 rounded-lg border border-border hover:border-primary transition-all"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xl">{getTypeIcon(task.type)}</span>
                      <h4 className="font-semibold text-foreground">{task.title}</h4>
                    </div>
                    <span className={`px-2 py-1 rounded text-xs font-semibold ${getPriorityColor(task.priority)}`}>
                      {task.priority}
                    </span>
                  </div>
                  {task.description && (
                    <p className="text-sm text-secondary mb-2">{task.description}</p>
                  )}
                  <div className="flex items-center justify-between text-xs text-secondary mb-3">
                    <div className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {format(new Date(task.due_date), 'MMM d, p')}
                    </div>
                    {task.assigned_name && (
                      <div className="flex items-center gap-1">
                        <User className="w-3 h-3" />
                        {task.assigned_name}
                      </div>
                    )}
                  </div>
                  <button
                    onClick={() => handleComplete(task.id)}
                    className="w-full py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary/90 transition-all"
                  >
                    Mark Complete
                  </button>
                </motion.div>
              ))}
            </div>
          </div>

          {/* Overdue */}
          <div>
            <h3 className="text-lg font-bold text-foreground mb-4 flex items-center gap-2">
              <div className="w-3 h-3 bg-red-500 rounded-full"></div>
              Overdue ({tasksByStatus.overdue.length})
            </h3>
            <div className="space-y-3">
              {tasksByStatus.overdue.map((task, index) => (
                <motion.div
                  key={task.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className="bg-red-50 p-4 rounded-lg border-2 border-red-200"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xl">{getTypeIcon(task.type)}</span>
                      <h4 className="font-semibold text-foreground">{task.title}</h4>
                    </div>
                    <span className={`px-2 py-1 rounded text-xs font-semibold ${getPriorityColor(task.priority)}`}>
                      {task.priority}
                    </span>
                  </div>
                  {task.description && (
                    <p className="text-sm text-secondary mb-2">{task.description}</p>
                  )}
                  <div className="flex items-center justify-between text-xs text-red-600 mb-3">
                    <div className="flex items-center gap-1 font-semibold">
                      <Clock className="w-3 h-3" />
                      {format(new Date(task.due_date), 'MMM d, p')}
                    </div>
                    {task.assigned_name && (
                      <div className="flex items-center gap-1">
                        <User className="w-3 h-3" />
                        {task.assigned_name}
                      </div>
                    )}
                  </div>
                  <button
                    onClick={() => handleComplete(task.id)}
                    className="w-full py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 transition-all"
                  >
                    Complete Now
                  </button>
                </motion.div>
              ))}
            </div>
          </div>

          {/* Completed */}
          <div>
            <h3 className="text-lg font-bold text-foreground mb-4 flex items-center gap-2">
              <div className="w-3 h-3 bg-green-500 rounded-full"></div>
              Completed ({tasksByStatus.completed.length})
            </h3>
            <div className="space-y-3">
              {tasksByStatus.completed.map((task, index) => (
                <motion.div
                  key={task.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className="bg-green-50 p-4 rounded-lg border border-green-200 opacity-75"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <CheckSquare className="w-5 h-5 text-green-600" />
                      <h4 className="font-semibold text-foreground line-through">{task.title}</h4>
                    </div>
                  </div>
                  {task.description && (
                    <p className="text-sm text-secondary mb-2">{task.description}</p>
                  )}
                  <div className="text-xs text-green-600 font-medium">
                    Completed {format(new Date(task.completed_at), 'MMM d, p')}
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default TasksPage;