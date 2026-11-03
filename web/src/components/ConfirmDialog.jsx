import { AlertTriangle, X } from 'lucide-react';

export default function ConfirmDialog({ task, onCancel, onConfirm, deleting }) {
  if (!task) return null;

  return (
    <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && !deleting && onCancel()}>
      <section className="dialog confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="delete-title">
        <button className="icon-button dialog-close" type="button" onClick={onCancel} disabled={deleting} aria-label="Close dialog">
          <X size={18} />
        </button>
        <span className="confirm-icon"><AlertTriangle size={22} /></span>
        <h2 id="delete-title">Delete this task?</h2>
        <p><strong>{task.title}</strong> will be permanently removed from your task list.</p>
        <div className="dialog-actions">
          <button className="button button-secondary" type="button" onClick={onCancel} disabled={deleting}>
            Keep task
          </button>
          <button className="button button-danger" type="button" onClick={onConfirm} disabled={deleting}>
            {deleting ? 'Deleting...' : 'Delete task'}
          </button>
        </div>
      </section>
    </div>
  );
}
