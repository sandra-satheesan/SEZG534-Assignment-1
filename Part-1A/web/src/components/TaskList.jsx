import { ClipboardList, Plus, SearchX } from 'lucide-react';
import TaskCard from './TaskCard.jsx';

export default function TaskList({
  tasks,
  loading,
  hasSearch,
  hasFilters,
  onAddTask,
  onEdit,
  onDelete,
  onAdvance,
}) {
  if (loading) {
    return (
      <div className="task-grid loading-grid" aria-live="polite" aria-label="Loading tasks">
        {Array.from({ length: 3 }, (_, index) => (
          <div className="task-skeleton" key={index}>
            <span /><span /><span /><span />
          </div>
        ))}
      </div>
    );
  }

  if (tasks.length === 0) {
    const filtered = hasSearch || hasFilters;
    const EmptyIcon = filtered ? SearchX : ClipboardList;
    return (
      <div className="empty-state">
        <span className="empty-icon"><EmptyIcon size={25} /></span>
        <h3>{filtered ? 'No tasks match your filters' : 'Your task list is clear'}</h3>
        <p>
          {filtered
            ? 'Try adjusting your search or filters to find what you need.'
            : 'A fresh start. Add a task and make today count.'}
        </p>
        {!filtered && (
          <button className="button button-primary" type="button" onClick={onAddTask}>
            <Plus size={16} />
            Create your first task
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="task-grid">
      {tasks.map((task) => (
        <TaskCard
          key={task.id}
          task={task}
          onEdit={onEdit}
          onDelete={onDelete}
          onAdvance={onAdvance}
        />
      ))}
    </div>
  );
}
