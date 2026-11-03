import { useEffect, useState } from 'react';
import { Check, Tag, X } from 'lucide-react';

export default function TaskForm({ task, onClose, onSubmit, submitting }) {
  const [values, setValues] = useState({
    title: task?.title ?? '',
    description: task?.description ?? '',
    priority: task?.priority ?? 'medium',
    tags: task?.tags.join(', ') ?? '',
  });

  useEffect(() => {
    function onKeyDown(event) {
      if (event.key === 'Escape' && !submitting) onClose();
    }
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [onClose, submitting]);

  function update(field, value) {
    setValues((current) => ({ ...current, [field]: value }));
  }

  function submit(event) {
    event.preventDefault();
    const tags = [...new Set(values.tags.split(',').map((tag) => tag.trim()).filter(Boolean))];
    onSubmit({
      title: values.title.trim(),
      description: values.description.trim(),
      priority: values.priority,
      tags,
    });
  }

  return (
    <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && !submitting && onClose()}>
      <section className="dialog task-form-dialog" role="dialog" aria-modal="true" aria-labelledby="task-form-title">
        <div className="dialog-heading">
          <div>
            <span className="dialog-kicker">{task ? 'UPDATE DETAILS' : 'NEW TASK'}</span>
            <h2 id="task-form-title">{task ? 'Edit task' : 'Create a task'}</h2>
          </div>
          <button className="icon-button" type="button" onClick={onClose} disabled={submitting} aria-label="Close dialog">
            <X size={18} />
          </button>
        </div>
        <p className="dialog-intro">
          {task
            ? 'Keep the details current. Your task status will stay as it is.'
            : 'Capture the next thing you want to get done.'}
        </p>
        <form className="task-form" onSubmit={submit}>
          <label>
            <span>Task title <b>*</b></span>
            <input
              autoFocus
              required
              maxLength={160}
              value={values.title}
              onChange={(event) => update('title', event.target.value)}
              placeholder="e.g. Prepare project update"
            />
          </label>
          <label>
            <span>Description <b>*</b></span>
            <textarea
              required
              rows={4}
              maxLength={2000}
              value={values.description}
              onChange={(event) => update('description', event.target.value)}
              placeholder="Add a few details to help you get started..."
            />
          </label>
          <div className="form-row">
            <label>
              <span>Priority <b>*</b></span>
              <select value={values.priority} onChange={(event) => update('priority', event.target.value)}>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </label>
            <label>
              <span>Tags</span>
              <div className="input-with-icon">
                <Tag size={15} />
                <input
                  value={values.tags}
                  onChange={(event) => update('tags', event.target.value)}
                  placeholder="work, planning"
                />
              </div>
            </label>
          </div>
          <div className="form-hint">Separate tags with commas. New tasks start as pending.</div>
          <div className="dialog-actions">
            <button className="button button-secondary" type="button" onClick={onClose} disabled={submitting}>
              Cancel
            </button>
            <button className="button button-primary" type="submit" disabled={submitting}>
              {submitting ? <span className="button-spinner" /> : <Check size={16} />}
              {submitting ? 'Saving...' : task ? 'Save changes' : 'Create task'}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
