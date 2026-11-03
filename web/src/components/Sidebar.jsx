import {
  BadgeCheck,
  CheckSquare2,
  CircleHelp,
  LayoutDashboard,
  ListTodo,
  Sparkles,
} from 'lucide-react';

const navigation = [
  { label: 'Overview', icon: LayoutDashboard, filter: null },
  { label: 'My tasks', icon: ListTodo, filter: 'all' },
  { label: 'Completed', icon: BadgeCheck, filter: 'completed' },
];

export default function Sidebar({ activeView, onNavigate, taskCount }) {
  return (
    <aside className="sidebar">
      <a className="brand" href="#" onClick={(event) => event.preventDefault()}>
        <span className="brand-mark"><CheckSquare2 size={21} strokeWidth={2.5} /></span>
        <span className="brand-copy">
          <strong>daylight</strong>
          <small>YOUR WORKSPACE</small>
        </span>
      </a>

      <div className="workspace-switcher">
        <span className="workspace-avatar">S</span>
        <span className="workspace-copy">
          <strong>Personal space</strong>
          <small>Free workspace</small>
        </span>
        <span className="workspace-menu" aria-hidden="true">···</span>
      </div>

      <div className="sidebar-label">WORKSPACE</div>
      <nav className="sidebar-nav" aria-label="Main navigation">
        {navigation.map(({ label, icon: Icon, filter }) => {
          const selected = activeView === filter;
          return (
            <button
              className={`nav-item${selected ? ' active' : ''}`}
              key={label}
              onClick={() => onNavigate(filter)}
              aria-current={selected ? 'page' : undefined}
            >
              <Icon size={18} />
              <span>{label}</span>
              {label === 'My tasks' && (
                <span className="nav-count">{taskCount}</span>
              )}
            </button>
          );
        })}
      </nav>

      <div className="sidebar-bottom">
        <div className="sidebar-tip">
          <span className="tip-icon"><Sparkles size={16} /></span>
          <strong>A little progress<br />goes a long way.</strong>
          <span className="tip-caption">Keep your momentum going.</span>
        </div>
        <button className="help-link" type="button" onClick={() => window.alert('Your tasks are saved securely by your task service.')}>
          <CircleHelp size={17} />
          <span>Help & support</span>
        </button>
        <div className="profile">
          <span className="profile-avatar">SS</span>
          <span className="profile-copy">
            <strong>My workspace</strong>
            <small>Task manager</small>
          </span>
          <span className="profile-status" title="Connected to task API" />
        </div>
      </div>
    </aside>
  );
}
