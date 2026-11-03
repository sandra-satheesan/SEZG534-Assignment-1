import { Bell, ChevronDown, Plus, Search } from 'lucide-react';

export default function Header({ onAddTask, search, onSearchChange }) {
  return (
    <header className="topbar">
      <div className="breadcrumb">
        <span>Workspace</span>
        <span className="breadcrumb-divider">/</span>
        <strong>My Tasks</strong>
      </div>
      <div className="topbar-actions">
        <label className="top-search">
          <Search size={16} />
          <input
            type="search"
            aria-label="Search tasks"
            placeholder="Search anything..."
            value={search}
            onChange={(event) => onSearchChange(event.target.value)}
          />
          <kbd>⌘ K</kbd>
        </label>
        <button className="icon-button notification-button" type="button" aria-label="Notifications">
          <Bell size={18} />
          <span />
        </button>
        <button className="top-profile" type="button" aria-label="Workspace profile">
          <span className="profile-avatar">SS</span>
          <ChevronDown size={14} />
        </button>
        <button className="button button-primary top-add" type="button" onClick={onAddTask}>
          <Plus size={17} />
          <span>Add task</span>
        </button>
      </div>
    </header>
  );
}
