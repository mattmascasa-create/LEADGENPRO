import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { DndContext, closestCenter, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { Plus } from 'lucide-react';
import { toast } from 'react-toastify';
import DashboardLayout from '@/components/DashboardLayout';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const PipelinePage = () => {
  const [leads, setLeads] = useState([]);

  const stages = [
    { id: 'prospecting', name: 'Prospecting', color: 'bg-slate-100' },
    { id: 'qualified', name: 'Qualified', color: 'bg-blue-100' },
    { id: 'proposal', name: 'Proposal', color: 'bg-yellow-100' },
    { id: 'negotiation', name: 'Negotiation', color: 'bg-orange-100' },
    { id: 'closed', name: 'Closed Won', color: 'bg-green-100' }
  ];

  useEffect(() => {
    fetchLeads();
  }, []);

  const fetchLeads = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/leads`);
      setLeads(response.data);
    } catch (error) {
      toast.error('Failed to load pipeline');
    }
  };

  const getLeadsByStage = (stage) => {
    return leads.filter(lead => lead.stage === stage);
  };

  return (
    <DashboardLayout>
      <div>
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-foreground mb-2">Sales Pipeline</h1>
          <p className="text-secondary">Manage your deals through each stage</p>
        </div>

        <div className="flex gap-4 overflow-x-auto pb-4">
          {stages.map((stage) => {
            const stageLeads = getLeadsByStage(stage.id);
            return (
              <div key={stage.id} className="flex-shrink-0 w-80">
                <div className={`${stage.color} rounded-lg p-4 mb-4`}>
                  <div className="flex items-center justify-between">
                    <h3 className="font-semibold text-foreground">{stage.name}</h3>
                    <span className="text-sm font-medium text-secondary">{stageLeads.length}</span>
                  </div>
                </div>
                <div className="space-y-3">
                  {stageLeads.map((lead) => (
                    <div
                      key={lead.id}
                      className="bg-white p-4 rounded-lg border border-border hover:border-primary transition-all duration-200 cursor-pointer"
                    >
                      <h4 className="font-semibold text-foreground mb-1">
                        {lead.first_name} {lead.last_name}
                      </h4>
                      <p className="text-sm text-secondary mb-2">{lead.company}</p>
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium metric-value text-primary">
                          Score: {lead.score}
                        </span>
                        <span className="text-xs text-secondary">{lead.email}</span>
                      </div>
                    </div>
                  ))}
                  {stageLeads.length === 0 && (
                    <p className="text-sm text-secondary text-center py-8">No leads in this stage</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </DashboardLayout>
  );
};

export default PipelinePage;