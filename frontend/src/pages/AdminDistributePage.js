import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Users, Target, Send } from 'lucide-react';
import { toast } from 'react-toastify';
import DashboardLayout from '@/components/DashboardLayout';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const AdminDistributePage = () => {
  const [employees, setEmployees] = useState([]);
  const [leads, setLeads] = useState([]);
  const [selectedEmployees, setSelectedEmployees] = useState([]);
  const [leadsPerEmployee, setLeadsPerEmployee] = useState(10);
  const [filterScore, setFilterScore] = useState(0);
  const [distributing, setDistributing] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [employeesRes, leadsRes] = await Promise.all([
        axios.get(`${API_URL}/api/users`),
        axios.get(`${API_URL}/api/leads`)
      ]);
      setEmployees(employeesRes.data.filter(u => u.role === 'employee'));
      setLeads(leadsRes.data.filter(l => !l.assigned_to));
    } catch (error) {
      toast.error('Failed to load data');
    }
  };

  const handleDistribute = async () => {
    if (selectedEmployees.length === 0) {
      toast.error('Please select at least one employee');
      return;
    }

    setDistributing(true);
    try {
      const response = await axios.post(`${API_URL}/api/admin/distribute-leads`, {
        employee_ids: selectedEmployees,
        count_per_employee: leadsPerEmployee,
        filters: { score_min: filterScore }
      });
      toast.success(response.data.message);
      fetchData();
      setSelectedEmployees([]);
    } catch (error) {
      toast.error('Distribution failed: ' + (error.response?.data?.detail || 'Unknown error'));
    } finally {
      setDistributing(false);
    }
  };

  const toggleEmployee = (employeeId) => {
    setSelectedEmployees(prev =>
      prev.includes(employeeId)
        ? prev.filter(id => id !== employeeId)
        : [...prev, employeeId]
    );
  };

  const unassignedLeads = leads.filter(l => !l.assigned_to && l.score >= filterScore);

  return (
    <DashboardLayout>
      <div>
        <h1 className="text-4xl font-bold text-foreground mb-2">Distribute Leads</h1>
        <p className="text-secondary mb-8">Assign leads to your sales team</p>

        <div className="grid lg:grid-cols-2 gap-6 mb-8">
          {/* Available Leads */}
          <div className="bg-white p-6 rounded-xl border border-border">
            <h3 className="text-xl font-semibold text-foreground mb-4">Available Leads</h3>
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">Minimum Score Filter</label>
              <input
                type="range"
                min="0"
                max="100"
                value={filterScore}
                onChange={(e) => setFilterScore(parseInt(e.target.value))}
                className="w-full"
              />
              <div className="flex justify-between text-sm text-secondary mt-1">
                <span>0</span>
                <span className="font-semibold text-primary">{filterScore}</span>
                <span>100</span>
              </div>
            </div>
            <div className="text-center p-8 bg-slate-50 rounded-lg">
              <Target className="w-16 h-16 text-primary mx-auto mb-3" />
              <div className="text-4xl font-bold metric-value text-primary mb-2">{unassignedLeads.length}</div>
              <div className="text-secondary">Unassigned Leads</div>
            </div>
          </div>

          {/* Distribution Settings */}
          <div className="bg-white p-6 rounded-xl border border-border">
            <h3 className="text-xl font-semibold text-foreground mb-4">Distribution Settings</h3>
            <div className="mb-6">
              <label className="block text-sm font-medium mb-2">Leads per Employee</label>
              <input
                type="number"
                min="1"
                max="100"
                value={leadsPerEmployee}
                onChange={(e) => setLeadsPerEmployee(parseInt(e.target.value))}
                className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <div className="mb-6">
              <p className="text-sm text-secondary mb-2">Selected: {selectedEmployees.length} employees</p>
              <p className="text-sm text-secondary">Total to distribute: {selectedEmployees.length * leadsPerEmployee} leads</p>
            </div>
            <button
              onClick={handleDistribute}
              disabled={distributing || selectedEmployees.length === 0 || unassignedLeads.length === 0}
              className="w-full py-3 bg-primary text-white rounded-lg font-semibold hover:bg-primary/90 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              <Send className="w-5 h-5" />
              {distributing ? 'Distributing...' : 'Distribute Leads'}
            </button>
          </div>
        </div>

        {/* Employee Selection */}
        <div className="bg-white p-6 rounded-xl border border-border">
          <h3 className="text-xl font-semibold text-foreground mb-4">Select Employees</h3>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {employees.map((employee) => (
              <button
                key={employee.id}
                onClick={() => toggleEmployee(employee.id)}
                className={`p-4 rounded-lg border-2 transition-all text-left ${
                  selectedEmployees.includes(employee.id)
                    ? 'border-primary bg-primary/5'
                    : 'border-border hover:border-primary/50'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-gradient-to-br from-primary to-accent rounded-full flex items-center justify-center text-white font-semibold">
                    {employee.full_name.charAt(0)}
                  </div>
                  <div>
                    <p className="font-semibold text-foreground">{employee.full_name}</p>
                    <p className="text-sm text-secondary">{employee.email}</p>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default AdminDistributePage;