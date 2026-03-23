import React, { useState } from 'react';
import { User, ClipboardList, Timer, Building, Armchair, ArrowRight } from 'lucide-react';

const RegistrationForm = ({ onStart }) => {
  const [formData, setFormData] = useState({
    candidateName: '',
    candidateId: '',
    examTitle: 'Final Semester AI Assessment 2024',
    examCode: 'AI-402-PROK',
    durationMinutes: 60,
    center: 'VIRTUAL-EXAM-NODE-01',
    seatNumber: 'V-882'
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'durationMinutes' ? parseInt(value) || 0 : value
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!formData.candidateName || !formData.candidateId || !formData.examTitle) {
      alert('Please fill in candidate name, ID, and exam title.');
      return;
    }
    onStart(formData);
  };

  return (
    <div className="min-h-[calc(100vh-100px)] flex items-center justify-center p-6">
      <div className="bg-slate-800/50 backdrop-blur-xl border border-slate-700 p-8 rounded-2xl shadow-2xl max-w-2xl w-full">
        <div className="text-center mb-10">
          <h2 className="text-3xl font-bold text-white mb-2">Student Registration</h2>
          <p className="text-slate-400">Please provide your details to begin the proctored session</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Candidate Name */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-300 flex items-center gap-2">
                <User className="w-4 h-4 text-blue-400" /> Candidate Name
              </label>
              <input
                type="text"
                name="candidateName"
                value={formData.candidateName}
                onChange={handleChange}
                placeholder="Full Name"
                className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all"
                required
              />
            </div>
 
            {/* Candidate ID */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-300 flex items-center gap-2">
                <ClipboardList className="w-4 h-4 text-blue-400" /> Candidate ID
              </label>
              <input
                type="text"
                name="candidateId"
                value={formData.candidateId}
                onChange={handleChange}
                placeholder="e.g. STU-2026-001"
                className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all"
                required
              />
            </div>
 
            {/* Exam Title */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-300 flex items-center gap-2">
                <ClipboardList className="w-4 h-4 text-blue-400" /> Exam Title
              </label>
              <input
                type="text"
                name="examTitle"
                value={formData.examTitle}
                onChange={handleChange}
                placeholder="e.g. Deep Learning Final"
                className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all"
                required
              />
            </div>
 
            {/* Exam Code */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-300 flex items-center gap-2">
                <ClipboardList className="w-4 h-4 text-blue-400" /> Exam Code
              </label>
              <input
                type="text"
                name="examCode"
                value={formData.examCode}
                onChange={handleChange}
                placeholder="e.g. DL-101"
                className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all"
              />
            </div>
 
            {/* Center */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-300 flex items-center gap-2">
                <Building className="w-4 h-4 text-blue-400" /> Exam Center
              </label>
              <input
                type="text"
                name="center"
                value={formData.center}
                onChange={handleChange}
                placeholder="e.g. Hall A"
                className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all"
              />
            </div>
 
            {/* Seat Number */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-300 flex items-center gap-2">
                <Armchair className="w-4 h-4 text-blue-400" /> Seat Number
              </label>
              <input
                type="text"
                name="seatNumber"
                value={formData.seatNumber}
                onChange={handleChange}
                placeholder="e.g. PC-42"
                className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all"
              />
            </div>
 
            {/* Duration */}
            <div className="space-y-2 md:col-span-2">
              <label className="text-sm font-medium text-slate-300 flex items-center gap-2">
                <Timer className="w-4 h-4 text-blue-400" /> Exam Duration (minutes)
              </label>
              <input
                type="number"
                name="durationMinutes"
                value={formData.durationMinutes}
                onChange={handleChange}
                className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all"
                min="1"
              />
            </div>
          </div>

          <button
            type="submit"
            className="w-full mt-8 bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded-xl shadow-lg shadow-blue-500/20 flex items-center justify-center gap-2 group transition-all"
          >
            Start Proctored Session <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
          </button>
        </form>
      </div>
    </div>
  );
};

export default RegistrationForm;
