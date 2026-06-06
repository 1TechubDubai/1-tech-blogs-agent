import React, { useState, useEffect } from "react";
import { 
  Bot, Target, Zap, Activity, 
  Plus, X, Search, Hash, AlertTriangle,
  Sparkles, Save, Server, AlertCircle, HelpCircle, ShieldAlert
} from "lucide-react";
import Navbar from "../components/navbar.jsx";

// API Configuration - Updated to handle standard Vite env variables
const API_BASE_URL = import.meta.env.VITE_API_URL || import.meta.env.REACT_APP_API_URL || "http://localhost:8000";

// --- CUSTOM CHIP/TAG INPUT COMPONENT ---
const ChipInput = ({ label, icon: Icon, values, onChange, placeholder, onSuggest, suggestLoading, suggestionType }) => {
  const [inputValue, setInputValue] = useState("");

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      const val = inputValue.trim().replace(/,$/, "");
      if (val && !values.includes(val)) {
        onChange([...values, val]);
      }
      setInputValue("");
    }
  };

  const removeValue = (indexToRemove) => {
    onChange(values.filter((_, index) => index !== indexToRemove));
  };

  const handleSuggestClick = async () => {
    if (onSuggest) {
      const newValues = await onSuggest(suggestionType, values);
      if (newValues && Array.isArray(newValues)) {
        // Deduplicate: only add items not already in values
        const uniqueNewValues = newValues.filter(item => !values.includes(item));
        onChange([...values, ...uniqueNewValues]);
      }
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex justify-between items-end">
        <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest flex items-center gap-2">
          {Icon && <Icon size={12} className="text-cyan-500" />}
          {typeof label === 'string' ? <span>{label}</span> : label}
        </label>
        {onSuggest && (
          <button 
            type="button"
            onClick={handleSuggestClick}
            disabled={suggestLoading}
            className="text-[9px] font-bold uppercase tracking-wider text-amber-400 hover:text-amber-300 flex items-center gap-1 transition-colors disabled:opacity-50"
          >
            <Sparkles size={10} /> {suggestLoading ? "Analyzing..." : "AI Suggest"}
          </button>
        )}
      </div>
      
      <div className="bg-black/50 border border-slate-800 rounded-2xl p-2 focus-within:border-cyan-500/50 transition-colors">
        <div className="flex flex-wrap gap-2 mb-2">
          {values.map((val, idx) => (
            <span key={idx} className="bg-slate-800 text-cyan-50 text-xs px-3 py-1.5 rounded-lg flex items-center gap-2 border border-slate-700">
              {val}
              <button type="button" onClick={() => removeValue(idx)} className="text-slate-400 hover:text-red-400">
                <X size={12} />
              </button>
            </span>
          ))}
        </div>
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={values.length === 0 ? placeholder : "Type and press enter..."}
          className="w-full bg-transparent text-sm p-2 outline-none placeholder:text-slate-600 placeholder:italic"
        />
      </div>
    </div>
  );
};

// --- ERROR NOTIFICATION COMPONENT (NEW) ---
const ErrorNotification = ({ message, onClose }) => (
  <div className="fixed top-24 left-1/2 -translate-x-1/2 z-50 bg-red-950/90 border border-red-500/50 backdrop-blur-md rounded-xl p-4 shadow-2xl flex items-center gap-3 animate-in fade-in slide-in-from-top-4">
    <AlertCircle className="text-red-500" size={20} />
    <p className="text-sm font-medium text-red-200">{message}</p>
    <button onClick={onClose} className="ml-2 text-red-400 hover:text-red-300 transition-colors">
      <X size={16} />
    </button>
  </div>
);

// --- PROFILE INFO TOOLTIP ---
const ProfileTooltip = () => (
  <div className="bg-slate-950/95 border border-slate-700 rounded-lg p-4 max-w-sm text-sm text-slate-300 space-y-2">
    <p className="font-bold text-cyan-400">What is a Profile?</p>
    <p>A profile defines the autonomous agent's behavior, content strategy, and governance rules. Think of it as the "personality" and operating instructions for your SEO agent.</p>
    <ul className="list-disc list-inside space-y-1 text-xs">
      <li><strong>Industries:</strong> Business sectors you want to target (e.g., AI, FinTech, Healthcare)</li>
      <li><strong>Technologies:</strong> Technical stack to focus on for content (e.g., Python, Kubernetes)</li>
      <li><strong>Keywords:</strong> Target search terms for ranking optimization</li>
      <li><strong>Brand Tone:</strong> How your content should sound (professional, technical, casual)</li>
      <li><strong>Risk Tier:</strong> How strict content approval should be</li>
      <li><strong>Exclusions:</strong> Topics to never write about (for brand safety)</li>
    </ul>
  </div>
);

// --- CREATE PROFILE MODAL ---
const CreateProfileModal = ({ onClose, onCreated, onCreateSubmit }) => {
  const [profileName, setProfileName] = useState("");
  const [loading, setLoading] = useState(false);

  const handleCreate = async () => {
    if (!profileName.trim()) {
      alert("Please enter a profile name");
      return;
    }
    setLoading(true);
    await onCreateSubmit(profileName);
    setLoading(false);
  };

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl p-8 max-w-md w-full space-y-6">
        <div>
          <h2 className="text-2xl font-black text-cyan-400 uppercase tracking-tight">Create New Profile</h2>
          <p className="text-slate-400 text-sm mt-2">Set up your autonomous agent's operating personality</p>
        </div>

        <div className="space-y-3">
          <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Profile Name</label>
          <input 
            type="text"
            value={profileName}
            onChange={(e) => setProfileName(e.target.value)}
            placeholder="e.g. Enterprise Tech Profile, SaaS Focus..."
            className="w-full bg-black border border-slate-700 p-3 rounded-lg text-sm outline-none focus:border-cyan-500 placeholder:text-slate-600"
          />
        </div>

        <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4 text-xs text-slate-300 space-y-2">
          <p className="font-bold text-slate-200">Default Configuration:</p>
          <ul className="space-y-1 list-disc list-inside">
            <li>Profile will start empty</li>
            <li>Use AI Suggest buttons to populate industries, tech, & keywords</li>
            <li>Manually add anything you want to exclude or customize</li>
            <li>Save and activate when ready</li>
          </ul>
        </div>

        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-3 bg-slate-800 hover:bg-slate-700 rounded-lg font-bold text-sm uppercase transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleCreate}
            disabled={loading}
            className="flex-1 px-4 py-3 bg-cyan-600 hover:bg-cyan-500 rounded-lg font-black text-sm uppercase transition-colors disabled:opacity-50"
          >
            {loading ? "Creating..." : "Create Profile"}
          </button>
        </div>
      </div>
    </div>
  );
};

// --- FIELD DESCRIPTION TOOLTIP ---
const FieldDescription = ({ text }) => (
  <div className="group relative inline-block">
    <HelpCircle size={14} className="text-slate-500 cursor-help hover:text-slate-400 transition-colors" />
    <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block bg-slate-950 border border-slate-700 rounded-lg p-3 text-xs text-slate-300 w-48 z-50 whitespace-normal shadow-xl">
      {text}
    </div>
  </div>
);

// --- MAIN PAGE COMPONENT ---
const AgentConfigPage = () => {
  
  // State
  const [globalEnabled, setGlobalEnabled] = useState(false);
  const [profiles, setProfiles] = useState([]);
  const [activeProfileId, setActiveProfileId] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [suggestLoading, setSuggestLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showProfileTooltip, setShowProfileTooltip] = useState(false);

  // Form State matching Python backend schema
  const [formData, setFormData] = useState({
    profile_name: "Primary Operations Profile",
    target_industries: [],
    technology_focus: [],
    ranking_goals: [],
    preferred_tone: "professional_insightful",
    exclusion_policies: [],
    max_posts_per_week: 3,
    approval_threshold_risk: "medium",
    topics_requiring_approval: []
  });

  // Fetch initial data
  useEffect(() => {
    const fetchSystemData = async () => {
      try {
        setLoading(true);
        
        let currentActiveId = "";
        let settingsData = null;

        // 1. Fetch Global Settings
        try {
          const settingsResponse = await fetch(`${API_BASE_URL}/admin/settings`);
          if (settingsResponse.ok) {
            settingsData = await settingsResponse.json();
            setGlobalEnabled(settingsData.is_autonomous_mode_enabled || false);
            currentActiveId = settingsData.active_profile_id || "";
          }
        } catch (settingsErr) {
          console.warn("Failed to load settings", settingsErr);
        }

        // 2. Fetch Profiles
        try {
          const profilesResponse = await fetch(`${API_BASE_URL}/admin/profiles`);
          if (profilesResponse.ok) {
            const profilesList = await profilesResponse.json();
            setProfiles(profilesList);

            // 3. Populate Form with Active Profile or First Profile
            if (profilesList.length > 0) {
              let selectedProfile = null;
              
              // Try to find active profile from settings
              if (currentActiveId) {
                selectedProfile = profilesList.find(p => p.id === currentActiveId);
              }
              
              // Fall back to first profile if not found
              if (!selectedProfile) {
                selectedProfile = profilesList[0];
                currentActiveId = profilesList[0].id;
              }
              
              setActiveProfileId(currentActiveId);
              setFormData(selectedProfile);
            }
          }
        } catch (profilesErr) {
          console.error("Failed to load profiles", profilesErr);
          setError("Failed to load profiles. Please refresh the page.");
        }
      } catch (err) {
        console.error("Failed to load agent configuration", err);
        setError("Failed to load configuration. Please check your connection.");
      } finally {
        setLoading(false);
      }
    };

    fetchSystemData();
  }, []);

  // Handle Master Toggle
  const handleToggleSystem = async () => {
    const newState = !globalEnabled;
    try {
      const response = await fetch(`${API_BASE_URL}/admin/settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          is_autonomous_mode_enabled: newState,
          active_profile_id: activeProfileId
        })
      });

      if (response.ok) {
        setGlobalEnabled(newState);
      } else {
        setError("Failed to update system settings");
        setGlobalEnabled(!newState); // Revert on fail
      }
    } catch (err) {
      console.error("Failed to update master switch", err);
      setError("Network error updating system settings");
      setGlobalEnabled(!newState); // Revert on fail
    }
  };

  // Load profile when selected
  const handleProfileSelect = (profileId) => {
    setActiveProfileId(profileId);
    const selectedProfile = profiles.find(p => p.id === profileId);
    if (selectedProfile) {
      setFormData(selectedProfile);
    }
  };

  // Create New Profile
  const handleCreateProfile = async (profileName) => {
    try {
      const newProfile = {
        profile_name: profileName,
        target_industries: [],
        technology_focus: [],
        ranking_goals: [],
        preferred_tone: "professional_insightful",
        exclusion_policies: [],
        max_posts_per_week: 3,
        approval_threshold_risk: "medium",
        topics_requiring_approval: []
      };

      const response = await fetch(`${API_BASE_URL}/admin/profiles`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newProfile)
      });

      if (response.ok) {
        const createdProfile = await response.json();
        setProfiles([...profiles, createdProfile]);
        setActiveProfileId(createdProfile.id);
        setFormData(createdProfile);
        setShowCreateModal(false);
        // Using alert for simplicity, but could be replaced with a toast notification system
        alert(`Profile "${profileName}" created successfully!`);
      } else {
        setError("Failed to create profile");
      }
    } catch (err) {
      console.error("Failed to create profile", err);
      setError("Error creating profile. Check your connection.");
    }
  };

  // Save Current Profile Configuration
  const handleSaveProfile = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (!activeProfileId) {
        setError("No profile selected");
        return;
      }

      const response = await fetch(`${API_BASE_URL}/admin/profiles/${activeProfileId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData)
      });

      if (response.ok) {
        // Update system settings to ensure this is active
        await fetch(`${API_BASE_URL}/admin/settings`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            is_autonomous_mode_enabled: globalEnabled,
            active_profile_id: activeProfileId
          })
        });
        
        alert("Agent profile synchronized successfully.");
      } else {
        setError("Failed to save profile configuration");
      }
    } catch (err) {
      console.error("Failed to save profile", err);
      setError("Error saving configuration. Check your connection.");
    } finally {
      setSaving(false);
    }
  };

  // Unified AI Suggestion Handler
  const handleAISuggestion = async (suggestionType, currentValues) => {
    if (!activeProfileId) {
      setError("Please select a profile first");
      setSuggestLoading(false);
      return null;
    }

    setSuggestLoading(true);
    try {
      const endpoints = {
        "industries": "/admin/suggest-industries",
        "technology": "/admin/suggest-technologies",
        "keywords": "/admin/suggest-keywords",
        "exclusions": "/admin/suggest-exclusions"
      };

      const endpoint = endpoints[suggestionType] || endpoints["keywords"];

      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          profile_id: activeProfileId,
          current_values: currentValues,
          limit: 5
        })
      });

      if (response.ok) {
        const result = await response.json();
        if (result.suggestions && Array.isArray(result.suggestions)) {
          return result.suggestions.map(s => typeof s === 'string' ? s : s.name || s.value || s);
        }
      } else {
        setError(`Failed to generate ${suggestionType} suggestions`);
      }
    } catch (err) {
      console.error(`Failed to suggest ${suggestionType}`, err);
      setError(`Error connecting to suggestion engine for ${suggestionType}`);
    } finally {
      setSuggestLoading(false);
    }
    return null;
  };

  if (loading) return (
    <div className="min-h-screen bg-[#020617] flex items-center justify-center text-cyan-500">
      <div className="flex flex-col items-center gap-3">
        <Activity className="animate-spin" size={32} />
        <p className="text-sm">Loading configuration...</p>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#020617] text-white bg-[radial-gradient(ellipse_at_top_left,_var(--tw-gradient-stops))] from-slate-900 via-black to-black pb-20">
      <Navbar />

      {error && <ErrorNotification message={error} onClose={() => setError(null)} />}
      
      {showCreateModal && (
        <CreateProfileModal 
          onClose={() => setShowCreateModal(false)}
          onCreateSubmit={handleCreateProfile}
        />
      )}

      <div className="max-w-7xl mx-auto px-4 sm:px-6 pt-24 sm:pt-32">
        
        {/* ── HEADER & MASTER CONTROL ── */}
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-6 mb-12">
          <div className="relative">
            <h1 className="text-3xl sm:text-4xl font-black uppercase tracking-tighter italic flex items-center gap-3">
              <Bot className="text-cyan-500" size={36} /> Autonomous <span className="text-cyan-500">Agent</span>
            </h1>
            <p className="text-slate-500 font-mono text-[10px] uppercase tracking-[0.3em] mt-1">Configure systemic SEO discovery & publishing loops</p>
            
            {/* Help Icon */}
            <button 
              onMouseEnter={() => setShowProfileTooltip(true)}
              onMouseLeave={() => setShowProfileTooltip(false)}
              className="absolute -right-8 top-0 text-slate-500 hover:text-cyan-400 transition-colors"
            >
              <Plus size={20} className="rotate-45" />
            </button>
            {showProfileTooltip && (
              <div className="absolute top-full left-0 lg:left-auto lg:right-0 mt-2 z-40">
                <ProfileTooltip />
              </div>
            )}
          </div>

          <div className="flex items-center gap-4 bg-slate-900/50 border border-slate-800 p-2 pr-6 rounded-3xl">
            <button 
              onClick={handleToggleSystem}
              className={`relative w-16 h-8 rounded-full transition-colors ${globalEnabled ? 'bg-cyan-500/20 border-cyan-500' : 'bg-slate-800 border-slate-700'} border flex items-center`}
            >
              <div className={`absolute w-6 h-6 rounded-full transition-all ${globalEnabled ? 'bg-cyan-400 left-9 shadow-[0_0_15px_rgba(34,211,238,0.6)]' : 'bg-slate-500 left-1'}`} />
            </button>
            <div className="flex flex-col">
              <span className={`text-xs font-black uppercase tracking-widest ${globalEnabled ? 'text-cyan-400' : 'text-slate-500'}`}>
                {globalEnabled ? "Agent Active" : "Agent Suspended"}
              </span>
              <span className="text-[9px] font-mono text-slate-500">Master Engine Control</span>
            </div>
          </div>
        </div>

        {/* Show message if no profiles */}
        {profiles.length === 0 && (
          <div className="bg-amber-900/30 border border-amber-700/50 rounded-2xl p-6 mb-8">
            <div className="flex items-start gap-4">
              <AlertTriangle className="text-amber-500 flex-shrink-0 mt-1" />
              <div className="flex-1">
                <h3 className="font-bold text-amber-400 mb-2">No Profiles Yet</h3>
                <p className="text-sm text-amber-200 mb-4">Start by creating your first operational profile. This defines how your autonomous agent discovers trends, targets industries, and generates content.</p>
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="px-4 py-2 bg-amber-600 hover:bg-amber-500 rounded-lg font-bold text-sm uppercase transition-colors flex items-center gap-2"
                >
                  <Plus size={16} /> Create First Profile
                </button>
              </div>
            </div>
          </div>
        )}

        {profiles.length > 0 && (
          <form onSubmit={handleSaveProfile} className="space-y-8">
          
            {/* ── PROFILE SELECTOR ── */}
            <div className="bg-slate-900/40 border border-slate-800/60 rounded-[2rem] p-6 lg:p-8 flex flex-col md:flex-row gap-6 items-center justify-between relative overflow-hidden">
              <div className="absolute top-0 right-0 w-64 h-64 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />
              
              <div className="flex-1 w-full space-y-2 relative z-10">
                <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest flex items-center gap-2"><Server size={12}/> Operational Profile</label>
                <select 
                  className="w-full bg-black border border-slate-700 py-4 pl-4 pr-12 rounded-xl text-sm font-bold text-cyan-50 outline-none focus:border-cyan-500 appearance-none cursor-pointer"
                  value={activeProfileId}
                  onChange={(e) => handleProfileSelect(e.target.value)}
                >
                  <option value="">-- Select Profile --</option>
                  {profiles.map(p => (
                    <option key={p.id} value={p.id}>{p.profile_name}</option>
                  ))}
                </select>
                <p className="text-[9px] text-slate-500 italic mt-1">Select the profile to edit or create a new one</p>
              </div>

              <div className="hidden md:block w-px h-16 bg-slate-800" />

              <div className="flex-1 w-full space-y-2 relative z-10">
                <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Internal Profile Name</label>
                <input 
                  className="w-full bg-transparent border-b border-slate-700 py-4 text-sm font-bold outline-none focus:border-cyan-500" 
                  value={formData.profile_name}
                  onChange={e => setFormData({...formData, profile_name: e.target.value})}
                  disabled={!activeProfileId}
                />
              </div>

              <button
                type="button"
                onClick={() => setShowCreateModal(true)}
                className="px-4 py-3 bg-slate-800/50 hover:bg-slate-700 border border-slate-700 rounded-lg font-bold text-sm uppercase flex items-center gap-2 transition-colors relative z-10"
              >
                <Plus size={16} /> New Profile
              </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            
              {/* ── DISCOVERY & STRATEGY ── */}
              <div className="bg-slate-900/20 border border-slate-800/60 rounded-[2rem] p-6 lg:p-8 space-y-8">
              <h2 className="text-lg font-black uppercase tracking-tight flex items-center gap-3 border-b border-slate-800 pb-4">
                <Target className="text-cyan-500" size={20} /> Discovery Parameters
              </h2>

              <ChipInput 
                label={
                  <div className="flex items-center gap-2">
                    <span>Target Industries</span>
                    <FieldDescription text="Sectors or industries where you have expertise and want to achieve high organic rankings. Examples: SaaS, E-commerce, EdTech, Healthcare, FinTech, AI." />
                  </div>
                }
                icon={Search}
                placeholder="e.g. Artificial Intelligence, FinTech, Healthcare..."
                values={formData.target_industries}
                onChange={(newVals) => setFormData({...formData, target_industries: newVals})}
                onSuggest={handleAISuggestion}
                suggestLoading={suggestLoading}
                suggestionType="industries"
              />

              <ChipInput 
                label={
                  <div className="flex items-center gap-2">
                    <span>Technology Focus Areas</span>
                    <FieldDescription text="Programming languages, frameworks, tools, and technologies relevant to your content. Examples: React, Python, Kubernetes, PostgreSQL, AWS, Blockchain. Agent will generate technical guides around these." />
                  </div>
                }
                icon={Zap}
                placeholder="e.g. Python, React, Vector Databases..."
                values={formData.technology_focus}
                onChange={(newVals) => setFormData({...formData, technology_focus: newVals})}
                onSuggest={handleAISuggestion}
                suggestLoading={suggestLoading}
                suggestionType="technology"
              />

              <ChipInput 
                label={
                  <div className="flex items-center gap-2">
                    <span>Primary Keywords & Ranking Goals</span>
                    <FieldDescription text="Target search terms and keywords you want to rank for. The agent will generate blog content optimized around these keywords. Start with 3-5 seed keywords, then expand with suggestions." />
                  </div>
                }
                icon={Hash}
                placeholder="Manually enter seed keywords..."
                values={formData.ranking_goals}
                onChange={(newVals) => setFormData({...formData, ranking_goals: newVals})}
                onSuggest={handleAISuggestion}
                suggestLoading={suggestLoading}
                suggestionType="keywords"
              />
            </div>

            {/* ── GOVERNANCE & TONE ── */}
            <div className="bg-slate-900/20 border border-slate-800/60 rounded-[2rem] p-6 lg:p-8 space-y-8">
              <h2 className="text-lg font-black uppercase tracking-tight flex items-center gap-3 border-b border-slate-800 pb-4">
                <ShieldAlert className="text-amber-500" size={20} /> Governance & Limits
              </h2>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest flex items-center gap-2">
                    Publish Cap (Per Week)
                    <FieldDescription text="Maximum number of blog posts the agent will publish automatically per week. Prevents over-publishing. Range: 1-14 posts." />
                  </label>
                  <input 
                    type="number"
                    min="1" max="14"
                    className="w-full bg-black/50 border border-slate-800 p-4 rounded-xl text-sm outline-none focus:border-cyan-500 text-center font-mono text-cyan-400" 
                    value={formData.max_posts_per_week}
                    onChange={e => setFormData({...formData, max_posts_per_week: parseInt(e.target.value) || 1})}
                  />
                </div>
                
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest flex items-center gap-2">
                    Brand Tone
                    <FieldDescription text="Voice and style of generated content. Professional: formal/research-driven. Technical: code-heavy deep dives. Casual: growth hacking/startup vibe. Executive: summary for decision makers." />
                  </label>
                  <select 
                    className="w-full bg-black/50 border border-slate-800 p-4 rounded-xl text-xs outline-none focus:border-cyan-500 appearance-none"
                    value={formData.preferred_tone}
                    onChange={e => setFormData({...formData, preferred_tone: e.target.value})}
                  >
                    <option value="professional_insightful">Professional & Insightful</option>
                    <option value="technical_deep_dive">Technical & Code-Heavy</option>
                    <option value="casual_startup">Casual & Startup Growth</option>
                    <option value="executive_summary">Executive Summary</option>
                  </select>
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest flex items-center gap-2">
                  <AlertTriangle size={12} className="text-red-400" /> Autonomy Risk Tier
                  <FieldDescription text="Low: Auto-publishes safe/evergreen content. Medium: Auto-publishes but monitors. High: All content goes to approval queue first. Choose based on comfort with autonomous publishing." />
                </label>
                <div className="flex bg-black/50 p-1.5 rounded-2xl border border-slate-800">
                  {["low", "medium", "high"].map(tier => (
                    <button 
                      key={tier}
                      type="button"
                      onClick={() => setFormData({...formData, approval_threshold_risk: tier})} 
                      className={`flex-1 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${
                        formData.approval_threshold_risk === tier 
                          ? (tier === 'low' ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/50" 
                          : tier === 'medium' ? "bg-amber-500/20 text-amber-400 border border-amber-500/50"
                          : "bg-red-500/20 text-red-400 border border-red-500/50")
                          : "text-slate-500 border border-transparent hover:bg-slate-800"
                      }`}
                    >
                      {tier} Risk
                    </button>
                  ))}
                </div>
                <p className="text-[9px] text-slate-500 italic mt-2 px-2">
                  * High risk forces all generated content into the "Pending Approval" queue. Low risk allows auto-publishing for safe topics.
                </p>
              </div>

              <ChipInput 
                label={
                  <div className="flex items-center gap-2">
                    <span>Banned Topics / Exclusions</span>
                    <FieldDescription text="Topics the agent will never write about for brand safety. Examples: Politics, Competitors, Controversial Topics. Prevent content that could damage brand reputation." />
                  </div>
                }
                placeholder="e.g. Politics, Crypto, Competitor Names..."
                values={formData.exclusion_policies}
                onChange={(newVals) => setFormData({...formData, exclusion_policies: newVals})}
                onSuggest={handleAISuggestion}
                suggestLoading={suggestLoading}
                suggestionType="exclusions"
              />
            </div>
          </div>

          <div className="pt-6 border-t border-slate-800">
            <button
              type="submit"
              disabled={saving}
              className="w-full sm:w-auto ml-auto px-10 py-5 bg-cyan-600 hover:bg-cyan-500 rounded-2xl font-black text-[11px] tracking-[0.3em] uppercase flex items-center justify-center gap-3 shadow-xl shadow-cyan-900/40 transition-all disabled:opacity-50"
            >
              {saving ? <Activity className="animate-spin" size={18} /> : <Save size={18} />}
              {saving ? "Synchronizing..." : "Save Agent Configuration"}
            </button>
          </div>

        </form>
        )}
      </div>
    </div>
  );
};

export default AgentConfigPage;