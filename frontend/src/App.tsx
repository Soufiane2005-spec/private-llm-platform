import { useEffect, useMemo, useState } from 'react'
import './App.css'

import { fetchJobs } from './api/job'
import { fetchModels } from './api/models'
import type { Job, JobStatus } from './types/job'
import type { ModelCatalogEntry } from './types/model'

type View = 'models' | 'jobs'

function App() {
  const [view, setView] = useState<View>('models')

  const [models, setModels] = useState<ModelCatalogEntry[]>([])
  const [modelsLoading, setModelsLoading] = useState(true)
  const [modelsError, setModelsError] = useState<string | null>(null)

  const [jobs, setJobs] = useState<Job[]>([])
  const [jobsLoading, setJobsLoading] = useState(true)
  const [jobsError, setJobsError] = useState<string | null>(null)

  useEffect(() => {
    async function loadModels() {
      try {
        const data = await fetchModels()
        setModels(data)
      } catch (err) {
        setModelsError(
          err instanceof Error ? err.message : 'Unable to load models.',
        )
      } finally {
        setModelsLoading(false)
      }
    }

    void loadModels()
  }, [])

  useEffect(() => {
    async function loadJobs() {
      try {
        const data = await fetchJobs()
        setJobs(data)
      } catch (err) {
        setJobsError(
          err instanceof Error ? err.message : 'Unable to load jobs.',
        )
      } finally {
        setJobsLoading(false)
      }
    }

    void loadJobs()
  }, [])

  const enabledModels = useMemo(
    () => models.filter((model) => model.enabled).length,
    [models],
  )

  const jobCounts = useMemo(
    () =>
      jobs.reduce<Record<JobStatus, number>>(
        (counts, job) => {
          counts[job.status] += 1
          return counts
        },
        {
          pending: 0,
          running: 0,
          completed: 0,
          failed: 0,
        },
      ),
    [jobs],
  )

  return (
    <main className="page">
      <header className="topbar">
        <div>
          <p className="platform-name">Private LLM Platform</p>
        </div>

        <nav className="navigation" aria-label="Platform navigation">
          <button
            type="button"
            className={`nav-button ${view === 'models' ? 'nav-active' : ''}`}
            onClick={() => setView('models')}
          >
            Models
          </button>

          <button
            type="button"
            className={`nav-button ${view === 'jobs' ? 'nav-active' : ''}`}
            onClick={() => setView('jobs')}
          >
            Jobs
          </button>
        </nav>
      </header>

      {view === 'models' ? (
        <>
          <section className="hero">
            <div>
              <p className="eyebrow">Model catalog</p>
              <h1>Model Management</h1>
              <p className="hero-copy">
                View the models available on the platform and the inference
                engine assigned to each deployment.
              </p>
            </div>

            <div className="summary-card">
              <span>Available models</span>
              <strong>{models.length}</strong>
            </div>
          </section>

          <section className="content">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Catalog</p>
                <h2>Models</h2>
              </div>

              {!modelsLoading && !modelsError && (
                <span className="status">
                  {enabledModels} enabled
                </span>
              )}
            </div>

            {modelsLoading && (
              <div className="state-card">
                <p>Loading model catalog...</p>
              </div>
            )}

            {modelsError && (
              <div className="state-card error-card">
                <strong>Unable to load models</strong>
                <p>{modelsError}</p>
              </div>
            )}

            {!modelsLoading && !modelsError && (
              <div className="model-grid">
                {models.map((model) => (
                  <article className="model-card" key={model.model_id}>
                    <div className="model-card-header">
                      <div>
                        <p className="model-id">{model.model_id}</p>
                        <h3>{model.display_name}</h3>
                      </div>

                      <span
                        className={
                          model.enabled
                            ? 'badge badge-enabled'
                            : 'badge badge-disabled'
                        }
                      >
                        {model.enabled ? 'Enabled' : 'Disabled'}
                      </span>
                    </div>

                    <dl className="model-details">
                      <div>
                        <dt>Engine</dt>
                        <dd>
                          <span
                            className={`engine-badge engine-${model.engine}`}
                          >
                            {model.engine}
                          </span>
                        </dd>
                      </div>

                      <div>
                        <dt>Engine model</dt>
                        <dd>{model.engine_model_id}</dd>
                      </div>

                      <div>
                        <dt>Context length</dt>
                        <dd>
                          {model.context_length
                            ? `${model.context_length.toLocaleString()} tokens`
                            : 'Not specified'}
                        </dd>
                      </div>
                    </dl>
                  </article>
                ))}
              </div>
            )}
          </section>
        </>
      ) : (
        <>
          <section className="hero">
            <div>
              <p className="eyebrow">Async processing</p>
              <h1>Job Visualization</h1>
              <p className="hero-copy">
                Monitor asynchronous platform jobs, execution status, retry
                attempts, and failures from one operational view.
              </p>
            </div>

            <div className="summary-card">
              <span>Tracked jobs</span>
              <strong>{jobs.length}</strong>
            </div>
          </section>

          <section className="content">
            <div className="job-summary-grid">
              <article className="job-summary-item">
                <span>Pending</span>
                <strong>{jobCounts.pending}</strong>
              </article>

              <article className="job-summary-item">
                <span>Running</span>
                <strong>{jobCounts.running}</strong>
              </article>

              <article className="job-summary-item">
                <span>Completed</span>
                <strong>{jobCounts.completed}</strong>
              </article>

              <article className="job-summary-item">
                <span>Failed</span>
                <strong>{jobCounts.failed}</strong>
              </article>
            </div>

            <div className="section-heading jobs-heading">
              <div>
                <p className="eyebrow">Queue</p>
                <h2>Jobs</h2>
              </div>

              {!jobsLoading && !jobsError && (
                <span className="status">
                  {jobs.length} tracked
                </span>
              )}
            </div>

            {jobsLoading && (
              <div className="state-card">
                <p>Loading jobs...</p>
              </div>
            )}

            {jobsError && (
              <div className="state-card error-card">
                <strong>Unable to load jobs</strong>
                <p>{jobsError}</p>
              </div>
            )}

            {!jobsLoading && !jobsError && jobs.length === 0 && (
              <div className="state-card empty-state">
                <strong>No jobs yet</strong>
                <p>
                  Jobs submitted to the asynchronous processing pipeline will
                  appear here.
                </p>
              </div>
            )}

            {!jobsLoading && !jobsError && jobs.length > 0 && (
              <div className="job-grid">
                {jobs.map((job) => (
                  <article className="job-card" key={job.job_id}>
                    <div className="job-card-header">
                      <div>
                        <p className="job-id">{job.job_id}</p>
                        <h3>{formatJobType(job.job_type)}</h3>
                      </div>

                      <JobStatusBadge status={job.status} />
                    </div>

                    <dl className="job-details">
                      <div>
                        <dt>Status</dt>
                        <dd>{formatStatus(job.status)}</dd>
                      </div>

                      <div>
                        <dt>Attempts</dt>
                        <dd>
                          {job.attempts} / {job.max_attempts}
                        </dd>
                      </div>

                      <div>
                        <dt>Retries remaining</dt>
                        <dd>
                          {Math.max(job.max_attempts - job.attempts, 0)}
                        </dd>
                      </div>
                    </dl>

                    {job.error && (
                      <div className="job-error">
                        <span>Error</span>
                        <p>{job.error}</p>
                      </div>
                    )}
                  </article>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </main>
  )
}

function JobStatusBadge({ status }: { status: JobStatus }) {
  return (
    <span className={`job-status job-status-${status}`}>
      <span className="job-status-dot" />
      {formatStatus(status)}
    </span>
  )
}

function formatStatus(status: JobStatus) {
  return status.charAt(0).toUpperCase() + status.slice(1)
}

function formatJobType(jobType: string) {
  return jobType
    .split(/[-_]/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

export default App