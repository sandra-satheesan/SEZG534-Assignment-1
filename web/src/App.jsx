import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ArrowRight,
  CheckCircle2,
  Cloud,
  Plus,
  Sparkles,
} from 'lucide-react';
import Sidebar from './components/Sidebar.jsx';
import Header from './components/Header.jsx';
import DashboardStats from './components/DashboardStats.jsx';
import FilterBar from './components/FilterBar.jsx';
import TaskList from './components/TaskList.jsx';
import TaskForm from './components/TaskForm.jsx';
import ConfirmDialog from './components/ConfirmDialog.jsx';
import { createTask, deleteTask, listTasks, updateTask } from './services/taskApi.js';

const INITIAL_FILTERS = { status: '', priority: '', tags: '', sort: '' };
const NEXT_STATUS_LABEL = {
  'in-progress': 'Task started',
  completed: 'Task completed',
};

function parseTags(value) {
  return [...new Set(value.split(',').map((tag) => tag.trim()).filter(Boolean))];
}

function greetingForTime(hour) {
  if (hour < 12) return 'Good morning';
  if (hour < 18) return 'Good afternoon';
  return 'Good evening';
}

export default function App() {
  const [tasks, setTasks] = useState([]);
  const [visibleTasks, setVisibleTasks] = useState([]);
  const [filters, setFilters] = useState(INITIAL_FILTERS);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [apiError, setApiError] = useState('');
  const [refreshKey, setRefreshKey] = useState(0);
  const [formTask, setFormTask] = useState(undefined);
  const [confirmTask, setConfirmTask] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [toast, setToast] = useState(null);
  const [activeView, setActiveView] = useState(null);
  const [now] = useState(() => new Date());

  const loadTasks = useCallback(async () => {
    try {
      const allTasks = await listTasks();
      setTasks(allTasks);
      setApiError('');
    } catch (error) {
      setApiError(error.message);
    }
  }, []);

  useEffect(() => {
    let active = true;
    const query = {
      ...(filters.status ? { status: filters.status } : {}),
      ...(filters.priority ? { priority: filters.priority } : {}),
      ...(filters.sort ? { sort: filters.sort } : {}),
      tags: parseTags(filters.tags),
    };

    setLoading(true);
    listTasks(query)
      .then((result) => {
        if (active) {
          setVisibleTasks(result);
          setApiError('');
        }
      })
      .catch((error) => {
        if (active) setApiError(error.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => { active = false; };
  }, [filters, refreshKey]);

  useEffect(() => {
    loadTasks();
  }, [loadTasks, refreshKey]);

  useEffect(() => {
    if (!toast) return undefined;
    const timeout = window.setTimeout(() => setToast(null), 3600);
    return () => window.clearTimeout(timeout);
  }, [toast]);

  const displayedTasks = useMemo(() => {
    const normalizedSearch = search.trim().toLocaleLowerCase();
    if (!normalizedSearch) return visibleTasks;
    return visibleTasks.filter((task) => (
      [task.title, task.description, ...task.tags]
        .join(' ')
        .toLocaleLowerCase()
        .includes(normalizedSearch)
    ));
  }, [search, visibleTasks]);

  function updateFilter(field, value) {
    setActiveView(null);
    setFilters((current) => ({ ...current, [field]: value }));
  }

  function resetFilters() {
    setActiveView(null);
    setFilters(INITIAL_FILTERS);
    setSearch('');
  }

  function navigate(filter) {
    setActiveView(filter);
    setSearch('');
    setFilters((current) => ({
      ...current,
      status: filter === 'completed' ? 'completed' : '',
      priority: '',
      tags: '',
      sort: '',
    }));
  }

  async function saveTask(values) {
    setSubmitting(true);
    try {
      if (formTask) {
        await updateTask(formTask.id, values);
        setToast({ type: 'success', message: 'Task details updated.' });
      } else {
        await createTask(values);
        setToast({ type: 'success', message: 'Your task has been created.' });
      }
      setFormTask(undefined);
      setRefreshKey((key) => key + 1);
    } catch (error) {
      setToast({ type: 'error', message: error.message });
    } finally {
      setSubmitting(false);
    }
  }

  async function advanceTask(task, status) {
    try {
      await updateTask(task.id, { status });
      setToast({ type: 'success', message: NEXT_STATUS_LABEL[status] });
      setRefreshKey((key) => key + 1);
    } catch (error) {
      setToast({ type: 'error', message: error.message });
    }
  }

  async function removeTask() {
    if (!confirmTask) return;
    setDeleting(true);
    try {
      await deleteTask(confirmTask.id);
      setToast({ type: 'success', message: 'Task deleted.' });
      setConfirmTask(null);
      setRefreshKey((key) => key + 1);
    } catch (error) {
      setToast({ type: 'error', message: error.message });
    } finally {
      setDeleting(false);
    }
  }

  const hasFilters = Boolean(filters.status || filters.priority || parseTags(filters.tags).length || filters.sort);
  const pageDate = new Intl.DateTimeFormat('en', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  }).format(now);
  const isConnected = !apiError;

  return (
    <div className="app-shell">
      <Sidebar
        activeView={activeView}
        onNavigate={navigate}
        taskCount={tasks.length}
      />
      <main className="main-panel">
        <Header
          onAddTask={() => setFormTask(null)}
          search={search}
          onSearchChange={setSearch}
        />
        <div className="page-content">
          {apiError && (
            <div className="connection-alert" role="alert">
              <Cloud size={17} />
              <span><strong>Unable to reach the task service.</strong> {apiError}</span>
              <button type="button" onClick={() => { setRefreshKey((key) => key + 1); loadTasks(); }}>
                Retry
              </button>
            </div>
          )}

          <section className="welcome-row">
            <div>
              <div className="eyebrow"><span className="eyebrow-dot" /> YOUR PERSONAL WORKSPACE</div>
              <h1>{greetingForTime(now.getHours())}, Sandra <span className="wave">✦</span></h1>
              <p>Make room for what matters. One task at a time.</p>
            </div>
            <div className="welcome-meta">
              <div className="date-label">{pageDate}</div>
              <div className={`api-status ${isConnected ? 'connected' : 'disconnected'}`}>
                <span />
                {isConnected ? 'Live task sync' : 'Service unavailable'}
              </div>
            </div>
          </section>

          <DashboardStats
            tasks={tasks}
            selectedStatus={filters.status || (activeView === 'all' ? 'all' : '')}
            onSelectStatus={(status) => {
              setActiveView(status === 'all' ? 'all' : null);
              setFilters((current) => ({ ...current, status: status === 'all' ? '' : status }));
            }}
          />

          <section className="tasks-section">
            <div className="section-title-row">
              <div>
                <div className="section-title-wrap">
                  <h2>Tasks</h2>
                  <span className="task-total">{displayedTasks.length}</span>
                </div>
                <p className="section-subtitle">A clear view of everything on your plate.</p>
              </div>
              <button className="button button-primary section-add" type="button" onClick={() => setFormTask(null)}>
                <Plus size={16} />
                Add task
              </button>
            </div>

            <FilterBar
              filters={filters}
              onChange={updateFilter}
              onReset={resetFilters}
              hasFilters={hasFilters}
            />

            <TaskList
              tasks={displayedTasks}
              loading={loading}
              hasSearch={Boolean(search.trim())}
              hasFilters={hasFilters}
              onAddTask={() => setFormTask(null)}
              onEdit={(task) => setFormTask(task)}
              onDelete={setConfirmTask}
              onAdvance={advanceTask}
            />
          </section>

          <footer className="page-footer">
            <span><Sparkles size={14} /> Small steps, meaningful progress.</span>
            <span className="footer-api"><CheckCircle2 size={14} /> {isConnected ? 'Synced with your API' : 'Waiting for API'}</span>
            <a href="#top" onClick={(event) => event.preventDefault()} aria-label="Back to top">
              Back to top <ArrowRight size={13} />
            </a>
          </footer>
        </div>
      </main>

      {formTask !== undefined && (
        <TaskForm
          task={formTask}
          onClose={() => !submitting && setFormTask(undefined)}
          onSubmit={saveTask}
          submitting={submitting}
        />
      )}
      <ConfirmDialog
        task={confirmTask}
        onCancel={() => !deleting && setConfirmTask(null)}
        onConfirm={removeTask}
        deleting={deleting}
      />
      {toast && (
        <div className={`toast toast-${toast.type}`} role={toast.type === 'error' ? 'alert' : 'status'}>
          {toast.type === 'success' ? <CheckCircle2 size={18} /> : <Cloud size={18} />}
          <span>{toast.message}</span>
          <button type="button" aria-label="Dismiss message" onClick={() => setToast(null)}>×</button>
        </div>
      )}
    </div>
  );
}
