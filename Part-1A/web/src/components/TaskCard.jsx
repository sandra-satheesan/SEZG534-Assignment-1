import {
  ArrowRight,
  CalendarDays,
  Check,
  Circle,
  CircleCheck,
  Clock3,
  MoreHorizontal,
  Pencil,
  Trash2,
} from 'lucide-react';

const STATUS_PRESENTATION = {
  pending: { label: 'Pending', icon: Circle, className: 'pending' },
  'in-progress': { label: 'In progress', icon: Clock3, className: 'in-progress' },
  completed: { label: 'Completed', icon: CircleCheck, className: 'completed' },
};

const NEXT_STEP = {
  pending: { label: 'Start task', status: 'in-progress' },
  'in-progress': { label: 'Mark complete', status: 'completed' },
};

export default function TaskCard({ task, onEdit, onDelete, onAdvance }) {
  const status = STATUS_PRESENTATION[task.status];
  const StatusIcon = status.icon;
  const nextStep = NEXT_STEP[task.status];

  return (
    <article className={`task-card task-${task.status}`}>
      <div className="task-card-top">
        <span className={`status-pill ${status.className}`}>
          <StatusIcon size={13} />
          {status.label}
        </span>
        <div className="task-actions">
          <button type="button" className="task-action" onClick={() => onEdit(task)} aria-label={`Edit ${task.title}`} title="Edit task">
            <Pencil size={15} />
          </button>
          <button type="button" className="task-action danger-action" onClick={() => onDelete(task)} aria-label={`Delete ${task.title}`} title="Delete task">
            <Trash2 size={15} />
          </button>
          <button type="button" className="task-action more-action" aria-label="More task options">
            <MoreHorizontal size={17} />
          </button>
        </div>
      </div>

      <h3 className="task-title">{task.title}</h3>
      <p className="task-description">{task.description}</p>

      <div className="task-tags">
        {task.tags.length > 0
          ? task.tags.map((tag) => <span className="task-tag" key={tag}>{tag}</span>)
          : <span className="no-tags">No tags</span>}
      </div>

      <div className="task-card-bottom">
        <span className={`priority-label priority-${task.priority}`}>
          <span className="priority-dot" />
          {task.priority} priority
        </span>
        <span className="task-date"><CalendarDays size={13} /> Added to list</span>
      </div>

      {nextStep && (
        <button
          className="task-next-step"
          type="button"
          onClick={() => onAdvance(task, nextStep.status)}
        >
          {task.status === 'pending' ? <ArrowRight size={14} /> : <Check size={14} />}
          {nextStep.label}
        </button>
      )}
    </article>
  );
}
