import { ArrowUpRight, Circle, CircleCheck, Clock3, ListTodo } from 'lucide-react';

const cards = [
  { key: 'all', label: 'Total tasks', icon: ListTodo, tone: 'violet' },
  { key: 'pending', label: 'Pending', icon: Circle, tone: 'amber' },
  { key: 'in-progress', label: 'In progress', icon: Clock3, tone: 'blue' },
  { key: 'completed', label: 'Completed', icon: CircleCheck, tone: 'green' },
];

export default function DashboardStats({ tasks, onSelectStatus, selectedStatus }) {
  const counts = {
    all: tasks.length,
    pending: tasks.filter((task) => task.status === 'pending').length,
    'in-progress': tasks.filter((task) => task.status === 'in-progress').length,
    completed: tasks.filter((task) => task.status === 'completed').length,
  };

  return (
    <section className="stats-grid" aria-label="Task statistics">
      {cards.map(({ key, label, icon: Icon, tone }) => (
        <button
          className={`stat-card ${selectedStatus === key ? 'stat-selected' : ''}`}
          type="button"
          key={key}
          onClick={() => onSelectStatus(key)}
          aria-label={`Show ${label.toLowerCase()} tasks: ${counts[key]}`}
        >
          <span className={`stat-icon ${tone}`}><Icon size={19} /></span>
          <span className="stat-label">{label}</span>
          <span className="stat-value">{counts[key]}</span>
          <span className="stat-footer">
            <span>{key === 'all' ? 'In your workspace' : 'Tasks in this status'}</span>
            <ArrowUpRight size={14} />
          </span>
        </button>
      ))}
    </section>
  );
}
