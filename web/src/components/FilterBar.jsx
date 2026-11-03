import { ArrowDownWideNarrow, ListFilter, RotateCcw, Tag } from 'lucide-react';

export default function FilterBar({ filters, onChange, onReset, hasFilters }) {
  return (
    <div className="filter-bar">
      <div className="filter-heading">
        <ListFilter size={16} />
        <span>Filter by</span>
      </div>
      <label className="filter-control">
        <span className="sr-only">Status</span>
        <select
          value={filters.status}
          onChange={(event) => onChange('status', event.target.value)}
          aria-label="Filter by status"
        >
          <option value="">All statuses</option>
          <option value="pending">Pending</option>
          <option value="in-progress">In progress</option>
          <option value="completed">Completed</option>
        </select>
      </label>
      <label className="filter-control">
        <span className="sr-only">Priority</span>
        <select
          value={filters.priority}
          onChange={(event) => onChange('priority', event.target.value)}
          aria-label="Filter by priority"
        >
          <option value="">All priorities</option>
          <option value="high">High priority</option>
          <option value="medium">Medium priority</option>
          <option value="low">Low priority</option>
        </select>
      </label>
      <label className="filter-control tag-filter">
        <Tag size={15} />
        <input
          value={filters.tags}
          onChange={(event) => onChange('tags', event.target.value)}
          placeholder="Tags, comma separated"
          aria-label="Filter by tags"
        />
      </label>
      <label className="filter-control sort-control">
        <ArrowDownWideNarrow size={15} />
        <select
          value={filters.sort}
          onChange={(event) => onChange('sort', event.target.value)}
          aria-label="Sort tasks"
        >
          <option value="">Default order</option>
          <option value="priority">Priority: high to low</option>
        </select>
      </label>
      {hasFilters && (
        <button className="reset-filters" type="button" onClick={onReset}>
          <RotateCcw size={14} />
          Reset
        </button>
      )}
    </div>
  );
}
