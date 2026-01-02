import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { 
  ArrowLeft, Mail, Phone, Building, User, Calendar, 
  MessageSquare, CheckCircle, Clock, Plus, Send, 
  Star, Tag, TrendingUp, Activity, FileText
} from 'lucide-react';
import { toast } from 'react-toastify';
import { format } from 'date-fns';
import { motion } from 'framer-motion';
import DashboardLayout from '@/components/DashboardLayout';
import CallModal from '@/components/CallModal';
import EmailModal from '@/components/EmailModal';
import MeetingModal from '@/components/MeetingModal';
import { useAuth } from '@/context/AuthContext';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const LeadDetailPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [lead, setLead] = useState(null);
  const [activities, setActivities] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('activity');
  const [showTaskForm, setShowTaskForm] = useState(false);
  const [showNoteForm, setShowNoteForm] = useState(false);
  const [showCallModal, setShowCallModal] = useState(false);
  const [showEmailModal, setShowEmailModal] = useState(false);
  const [showMeetingModal, setShowMeetingModal] = useState(false);
  const [noteContent, setNoteContent] = useState('');
  const [taskForm, setTaskForm] = useState({
    title: '',
    description: '',
    type: 'call',
    due_date: '',
    priority: 'medium'
  });

  useEffect(() => {
    fetchLeadData();
  }, [id]);

  const fetchLeadData = async () => {
    try {
      const [leadRes, activitiesRes, tasksRes] = await Promise.all([
        axios.get(`${API_URL}/api/leads/${id}`),
        axios.get(`${API_URL}/api/activities?lead_id=${id}`),
        axios.get(`${API_URL}/api/tasks?lead_id=${id}`)
      ]);
      setLead(leadRes.data);
      setActivities(activitiesRes.data.filter(a => a.lead_id === id));
      setTasks(tasksRes.data.filter(t => t.lead_id === id));
    } catch (error) {
      toast.error('Failed to load lead details');
    } finally {
      setLoading(false);
    }
  };

  const handleStageChange = async (newStage) => {
    try {
      await axios.post(`${API_URL}/api/leads/${id}/stage?stage=${newStage}`);
      toast.success(`Lead moved to ${newStage}`);
      fetchLeadData();
    } catch (error) {
      toast.error('Failed to update stage');
    }
  };

  const handleCreateTask = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API_URL}/api/tasks`, {
        ...taskForm,
        lead_id: id,
        assigned_to: user.id
      });
      toast.success('Task created!');
      setShowTaskForm(false);
      setTaskForm({ title: '', description: '', type: 'call', due_date: '', priority: 'medium' });
      fetchLeadData();
    } catch (error) {
      toast.error('Failed to create task');
    }
  };

  const handleCompleteTask = async (taskId) => {
    try {
      await axios.put(`${API_URL}/api/tasks/${taskId}/complete`);
      toast.success('Task completed!');
      fetchLeadData();
    } catch (error) {
      toast.error('Failed to complete task');
    }
  };

  const getActivityIcon = (type) => {
    const icons = {
      lead_created: <Plus className="w-4 h-4" />,
      stage_changed: <TrendingUp className="w-4 h-4" />,
      call_logged: <Phone className="w-4 h-4" />,
      email_sent: <Mail className="w-4 h-4" />,
      task_created: <CheckCircle className="w-4 h-4" />,
      task_completed: <CheckCircle className="w-4 h-4" />,
      meeting_scheduled: <Calendar className="w-4 h-4" />,
      note_added: <FileText className="w-4 h-4" />
    };
    return icons[type] || <Activity className="w-4 h-4" />;
  };

  const getActivityColor = (type) => {
    const colors = {
      lead_created: 'bg-green-100 text-green-600',
      stage_changed: 'bg-blue-100 text-blue-600',
      call_logged: 'bg-purple-100 text-purple-600',
      email_sent: 'bg-orange-100 text-orange-600',
      task_created: 'bg-yellow-100 text-yellow-600',
      task_completed: 'bg-green-100 text-green-600',
      meeting_scheduled: 'bg-indigo-100 text-indigo-600',
      note_added: 'bg-gray-100 text-gray-600'
    };
    return colors[type] || 'bg-gray-100 text-gray-600';
  };

  const stages = ['prospecting', 'qualified', 'proposal', 'negotiation', 'closed'];

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center min-h-[50vh]">
          <div className="text-primary text-xl">Loading...</div>
        </div>
      </DashboardLayout>
    );
  }

  if (!lead) {
    return (
      <DashboardLayout>
        <div className="text-center py-12">
          <p className="text-secondary">Lead not found</p>
          <button onClick={() => navigate('/leads')} className="mt-4 text-primary hover:underline">
            Back to Leads
          </button>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div>
        {/* Header */}
        <div className="flex items-center gap-4 mb-6">
          <button 
            onClick={() => navigate('/leads')}
            className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="flex-1">
            <h1 className="text-3xl font-bold text-foreground">
              {lead.first_name} {lead.last_name}
            </h1>
            <p className="text-secondary flex items-center gap-2">
              <Building className="w-4 h-4" />
              {lead.company} {lead.title && `• ${lead.title}`}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <div className="text-3xl font-bold text-primary">{lead.score}</div>
              <div className="text-xs text-secondary">Lead Score</div>
            </div>
          </div>
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Left Column - Lead Info */}
          <div className="lg:col-span-1 space-y-6">
            {/* Contact Info Card */}
            <div className="bg-white p-6 rounded-xl border border-border">
              <h3 className="font-semibold text-foreground mb-4">Contact Information</h3>
              <div className="space-y-3">
                <a href={`mailto:${lead.email}`} className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors">
                  <Mail className="w-5 h-5 text-primary" />
                  <span className="text-sm">{lead.email}</span>
                </a>
                {lead.phone && (
                  <a href={`tel:${lead.phone}`} className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors">
                    <Phone className="w-5 h-5 text-green-600" />
                    <span className="text-sm">{lead.phone}</span>
                  </a>
                )}
                <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
                  <Building className="w-5 h-5 text-secondary" />
                  <span className="text-sm">{lead.company}</span>
                </div>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="bg-white p-6 rounded-xl border border-border">
              <h3 className="font-semibold text-foreground mb-4">Quick Actions</h3>
              <div className="grid grid-cols-3 gap-2">
                <button 
                  onClick={() => setShowCallModal(true)}
                  className="flex flex-col items-center gap-2 p-3 bg-green-50 rounded-lg hover:bg-green-100 transition-colors"
                >
                  <Phone className="w-5 h-5 text-green-600" />
                  <span className="text-xs font-medium text-green-600">Call</span>
                </button>
                <button 
                  onClick={() => setShowEmailModal(true)}
                  className="flex flex-col items-center gap-2 p-3 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
                >
                  <Mail className="w-5 h-5 text-blue-600" />
                  <span className="text-xs font-medium text-blue-600">Email</span>
                </button>
                <button 
                  onClick={() => setShowMeetingModal(true)}
                  className="flex flex-col items-center gap-2 p-3 bg-purple-50 rounded-lg hover:bg-purple-100 transition-colors"
                >
                  <Calendar className="w-5 h-5 text-purple-600" />
                  <span className="text-xs font-medium text-purple-600">Meet</span>
                </button>
              </div>
            </div>

            {/* Pipeline Stage */}
            <div className="bg-white p-6 rounded-xl border border-border">
              <h3 className="font-semibold text-foreground mb-4">Pipeline Stage</h3>
              <div className="space-y-2">
                {stages.map((stage) => (
                  <button
                    key={stage}
                    onClick={() => handleStageChange(stage)}
                    className={`w-full p-3 rounded-lg text-left text-sm font-medium capitalize transition-all ${
                      lead.stage === stage
                        ? 'bg-primary text-white'
                        : 'bg-slate-50 text-foreground hover:bg-slate-100'
                    }`}
                  >
                    {stage.replace('_', ' ')}
                  </button>
                ))}
              </div>
            </div>

            {/* AI Insights */}
            {lead.ai_insights && (
              <div className="bg-gradient-to-br from-orange-50 to-yellow-50 p-6 rounded-xl border border-orange-200">
                <h3 className="font-semibold text-foreground mb-3 flex items-center gap-2">
                  <Star className="w-5 h-5 text-orange-500" />
                  AI Insights
                </h3>
                <p className="text-sm text-foreground">{lead.ai_insights}</p>
              </div>
            )}

            {/* Tags */}
            {lead.tags && lead.tags.length > 0 && (
              <div className="bg-white p-6 rounded-xl border border-border">
                <h3 className="font-semibold text-foreground mb-3 flex items-center gap-2">
                  <Tag className="w-5 h-5" />
                  Tags
                </h3>
                <div className="flex flex-wrap gap-2">
                  {lead.tags.map((tag, idx) => (
                    <span key={idx} className="px-3 py-1 bg-slate-100 text-slate-700 rounded-full text-sm">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Right Column - Activity & Tasks */}
          <div className="lg:col-span-2">
            {/* Tabs */}
            <div className="flex gap-2 mb-6">
              <button
                onClick={() => setActiveTab('activity')}
                className={`px-4 py-2 rounded-lg font-medium transition-all ${
                  activeTab === 'activity' ? 'bg-primary text-white' : 'bg-slate-100 hover:bg-slate-200'
                }`}
              >
                Activity History
              </button>
              <button
                onClick={() => setActiveTab('tasks')}
                className={`px-4 py-2 rounded-lg font-medium transition-all ${
                  activeTab === 'tasks' ? 'bg-primary text-white' : 'bg-slate-100 hover:bg-slate-200'
                }`}
              >
                Tasks ({tasks.length})
              </button>
            </div>

            {/* Activity Timeline */}
            {activeTab === 'activity' && (
              <div className="bg-white rounded-xl border border-border">
                <div className="p-6 border-b border-border">
                  <h3 className="font-semibold text-foreground">Activity Timeline</h3>
                </div>
                <div className="p-6">
                  {activities.length > 0 ? (
                    <div className="relative">
                      <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-slate-200"></div>
                      <div className="space-y-6">
                        {activities.map((activity, index) => (
                          <motion.div
                            key={activity.id}
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: index * 0.05 }}
                            className="relative pl-10"
                          >
                            <div className={`absolute left-0 w-8 h-8 rounded-full flex items-center justify-center ${getActivityColor(activity.type)}`}>
                              {getActivityIcon(activity.type)}
                            </div>
                            <div className="bg-slate-50 p-4 rounded-lg">
                              <div className="flex items-center justify-between mb-1">
                                <span className="font-medium text-foreground capitalize">
                                  {activity.type.replace('_', ' ')}
                                </span>
                                <span className="text-xs text-secondary">
                                  {format(new Date(activity.created_at), 'MMM d, yyyy h:mm a')}
                                </span>
                              </div>
                              <p className="text-sm text-secondary">{activity.description}</p>
                            </div>
                          </motion.div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-12 text-secondary">
                      <Activity className="w-12 h-12 mx-auto mb-3 opacity-50" />
                      <p>No activity recorded yet</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Tasks Tab */}
            {activeTab === 'tasks' && (
              <div className="bg-white rounded-xl border border-border">
                <div className="p-6 border-b border-border flex items-center justify-between">
                  <h3 className="font-semibold text-foreground">Tasks</h3>
                  <button
                    onClick={() => setShowTaskForm(!showTaskForm)}
                    className="px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary/90 flex items-center gap-2"
                  >
                    <Plus className="w-4 h-4" />
                    Add Task
                  </button>
                </div>

                {/* Task Form */}
                {showTaskForm && (
                  <div className="p-6 border-b border-border bg-slate-50">
                    <form onSubmit={handleCreateTask} className="space-y-4">
                      <input
                        type="text"
                        placeholder="Task title"
                        value={taskForm.title}
                        onChange={(e) => setTaskForm({...taskForm, title: e.target.value})}
                        required
                        className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                      />
                      <div className="grid grid-cols-3 gap-3">
                        <select
                          value={taskForm.type}
                          onChange={(e) => setTaskForm({...taskForm, type: e.target.value})}
                          className="px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                        >
                          <option value="call">📞 Call</option>
                          <option value="email">📧 Email</option>
                          <option value="meeting">🗓️ Meeting</option>
                          <option value="follow_up">🔔 Follow Up</option>
                        </select>
                        <select
                          value={taskForm.priority}
                          onChange={(e) => setTaskForm({...taskForm, priority: e.target.value})}
                          className="px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                        >
                          <option value="low">Low</option>
                          <option value="medium">Medium</option>
                          <option value="high">High</option>
                        </select>
                        <input
                          type="datetime-local"
                          value={taskForm.due_date}
                          onChange={(e) => setTaskForm({...taskForm, due_date: e.target.value})}
                          required
                          className="px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                        />
                      </div>
                      <div className="flex gap-3">
                        <button type="submit" className="flex-1 py-2 bg-primary text-white rounded-lg font-medium">
                          Create Task
                        </button>
                        <button
                          type="button"
                          onClick={() => setShowTaskForm(false)}
                          className="px-4 py-2 border border-border rounded-lg"
                        >
                          Cancel
                        </button>
                      </div>
                    </form>
                  </div>
                )}

                <div className="p-6">
                  {tasks.length > 0 ? (
                    <div className="space-y-3">
                      {tasks.map((task) => (
                        <div
                          key={task.id}
                          className={`p-4 rounded-lg border ${
                            task.completed ? 'bg-green-50 border-green-200' : 'bg-white border-border'
                          }`}
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex items-center gap-3">
                              {!task.completed && (
                                <button
                                  onClick={() => handleCompleteTask(task.id)}
                                  className="w-6 h-6 rounded border-2 border-primary hover:bg-primary/10 transition-colors"
                                />
                              )}
                              {task.completed && (
                                <CheckCircle className="w-6 h-6 text-green-600" />
                              )}
                              <div>
                                <h4 className={`font-medium ${task.completed ? 'line-through text-secondary' : 'text-foreground'}`}>
                                  {task.title}
                                </h4>
                                <div className="flex items-center gap-3 text-xs text-secondary mt-1">
                                  <span className="flex items-center gap-1">
                                    <Clock className="w-3 h-3" />
                                    {format(new Date(task.due_date), 'MMM d, p')}
                                  </span>
                                  <span className={`px-2 py-0.5 rounded ${
                                    task.priority === 'high' ? 'bg-red-100 text-red-600' :
                                    task.priority === 'medium' ? 'bg-yellow-100 text-yellow-600' :
                                    'bg-green-100 text-green-600'
                                  }`}>
                                    {task.priority}
                                  </span>
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-12 text-secondary">
                      <CheckCircle className="w-12 h-12 mx-auto mb-3 opacity-50" />
                      <p>No tasks for this lead</p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Call Modal */}
      <CallModal
        isOpen={showCallModal}
        onClose={() => setShowCallModal(false)}
        lead={lead}
        onCallLogged={fetchLeadData}
      />

      {/* Email Modal */}
      <EmailModal
        isOpen={showEmailModal}
        onClose={() => setShowEmailModal(false)}
        singleLead={lead}
      />

      {/* Meeting Modal */}
      <MeetingModal
        isOpen={showMeetingModal}
        onClose={() => setShowMeetingModal(false)}
        lead={lead}
        onMeetingScheduled={fetchLeadData}
      />
    </DashboardLayout>
  );
};

export default LeadDetailPage;
