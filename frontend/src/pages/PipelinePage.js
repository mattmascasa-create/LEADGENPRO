import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { toast } from 'react-toastify';
import DashboardLayout from '@/components/DashboardLayout';
import {
  DndContext,
  DragOverlay,
  closestCorners,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Draggable Lead Card Component
const DraggableLeadCard = ({ lead }) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: lead.id,
    data: {
      type: 'lead',
      lead,
    },
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className="bg-white p-3 lg:p-4 rounded-lg border border-border hover:border-primary transition-all duration-200 cursor-grab active:cursor-grabbing shadow-sm"
    >
      <h4 className="font-semibold text-foreground mb-1 text-sm lg:text-base truncate">
        {lead.first_name} {lead.last_name}
      </h4>
      <p className="text-xs lg:text-sm text-secondary mb-2 truncate">{lead.company}</p>
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-primary">
          Score: {lead.score}
        </span>
        <span className="text-xs text-secondary truncate max-w-[80px] lg:max-w-[120px]">{lead.email}</span>
      </div>
    </div>
  );
};

// Static Lead Card for Overlay
const LeadCard = ({ lead }) => (
  <div className="bg-white p-4 rounded-lg border-2 border-primary shadow-lg w-72">
    <h4 className="font-semibold text-foreground mb-1">
      {lead.first_name} {lead.last_name}
    </h4>
    <p className="text-sm text-secondary mb-2">{lead.company}</p>
    <div className="flex items-center justify-between">
      <span className="text-xs font-medium text-primary">
        Score: {lead.score}
      </span>
      <span className="text-xs text-secondary truncate max-w-[120px]">{lead.email}</span>
    </div>
  </div>
);

// Droppable Stage Column Component
const StageColumn = ({ stage, children }) => {
  const { setNodeRef, isOver } = useSortable({
    id: stage.id,
    data: {
      type: 'stage',
      stage,
    },
  });

  return (
    <div ref={setNodeRef} className="flex-shrink-0 w-64 lg:w-80">
      <div className={`${stage.color} rounded-lg p-3 lg:p-4 mb-3 lg:mb-4`}>
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-foreground text-sm lg:text-base">{stage.name}</h3>
          <span className="text-xs lg:text-sm font-medium text-secondary">
            {React.Children.count(children)}
          </span>
        </div>
      </div>
      <div
        className={`space-y-2 lg:space-y-3 min-h-[200px] p-2 rounded-lg transition-colors ${
          isOver ? 'bg-primary/10 border-2 border-dashed border-primary' : ''
        }`}
      >
        {children}
        {React.Children.count(children) === 0 && (
          <p className="text-xs lg:text-sm text-secondary text-center py-8">
            Drop leads here
          </p>
        )}
      </div>
    </div>
  );
};

const PipelinePage = () => {
  const [leads, setLeads] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [activeLead, setActiveLead] = useState(null);

  const stages = [
    { id: 'prospecting', name: 'Prospecting', color: 'bg-slate-100' },
    { id: 'qualified', name: 'Qualified', color: 'bg-blue-100' },
    { id: 'proposal', name: 'Proposal', color: 'bg-yellow-100' },
    { id: 'negotiation', name: 'Negotiation', color: 'bg-orange-100' },
    { id: 'closed', name: 'Closed Won', color: 'bg-green-100' },
  ];

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    })
  );

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

  const getLeadsByStage = (stageId) => {
    return leads.filter((lead) => lead.stage === stageId);
  };

  const handleDragStart = (event) => {
    const { active } = event;
    setActiveId(active.id);
    const lead = leads.find((l) => l.id === active.id);
    setActiveLead(lead);
  };

  const handleDragOver = (event) => {
    const { active, over } = event;
    if (!over) return;

    const activeData = active.data.current;
    const overData = over.data.current;

    // Only handle lead drops
    if (activeData?.type !== 'lead') return;

    // Determine target stage
    let targetStageId = null;
    if (overData?.type === 'stage') {
      targetStageId = over.id;
    } else if (overData?.type === 'lead') {
      const overLead = leads.find((l) => l.id === over.id);
      if (overLead) {
        targetStageId = overLead.stage;
      }
    }

    if (!targetStageId) return;

    // Update lead stage locally for immediate feedback
    const activeLead = leads.find((l) => l.id === active.id);
    if (activeLead && activeLead.stage !== targetStageId) {
      setLeads((prev) =>
        prev.map((lead) =>
          lead.id === active.id ? { ...lead, stage: targetStageId } : lead
        )
      );
    }
  };

  const handleDragEnd = async (event) => {
    const { active, over } = event;
    setActiveId(null);
    setActiveLead(null);

    if (!over) return;

    const activeData = active.data.current;
    const overData = over.data.current;

    if (activeData?.type !== 'lead') return;

    // Determine final target stage
    let targetStageId = null;
    if (overData?.type === 'stage') {
      targetStageId = over.id;
    } else if (overData?.type === 'lead') {
      const overLead = leads.find((l) => l.id === over.id);
      if (overLead) {
        targetStageId = overLead.stage;
      }
    }

    if (!targetStageId) return;

    // Update on server
    try {
      await axios.post(`${API_URL}/api/leads/${active.id}/stage?stage=${targetStageId}`);
      toast.success(`Lead moved to ${stages.find((s) => s.id === targetStageId)?.name}`);
    } catch (error) {
      toast.error('Failed to update lead stage');
      fetchLeads(); // Revert on error
    }
  };

  return (
    <DashboardLayout>
      <div>
        <div className="mb-6 lg:mb-8">
          <h1 className="text-2xl lg:text-4xl font-bold text-foreground mb-1 lg:mb-2">Sales Pipeline</h1>
          <p className="text-sm lg:text-base text-secondary">Drag and drop leads to move them through stages</p>
        </div>

        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={handleDragStart}
          onDragOver={handleDragOver}
          onDragEnd={handleDragEnd}
        >
          <div className="flex gap-3 lg:gap-4 overflow-x-auto pb-4 -mx-4 px-4 lg:mx-0 lg:px-0">
            {stages.map((stage) => (
              <StageColumn key={stage.id} stage={stage}>
                {getLeadsByStage(stage.id).map((lead) => (
                  <DraggableLeadCard key={lead.id} lead={lead} />
                ))}
              </StageColumn>
            ))}
          </div>

          <DragOverlay>
            {activeLead ? <LeadCard lead={activeLead} /> : null}
          </DragOverlay>
        </DndContext>
      </div>
    </DashboardLayout>
  );
};

export default PipelinePage;