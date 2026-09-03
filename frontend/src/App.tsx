import { useEffect, useMemo, useState } from 'react'

import './App.css'

import { fetchBenchmarkReport, fetchBenchmarks } from './api/benchmarks'
import { fetchJobs } from './api/job'
import { fetchModels } from './api/models'
import { fetchMonitoringDashboard } from './api/monitoring'
import { ChatView } from './components/ChatView'
import type {
  BenchmarkRecord,
  BenchmarkReport,
} from './types/benchmark'
import type { Job, JobStatus } from './types/job'
import type { ModelCatalogEntry } from './types/model'
import type { MonitoringDashboard } from './types/monitoring'

type View = 'models' | 'jobs' | 'benchmarks' | 'monitoring' | 'chat'

interface ChartDatum {
  label: string
  value: number
  secondaryLabel?: string
}

interface ResourceDatum {
  label: string
  value: number | null
}

interface EngineBenchmarkAverage {
  engine: string
  count: number
  latency: number
  throughput: number
  cpu: number
  memory: number
  gpu: number | null
}

function App() {
  const [view, setView] = useState<View>('models')

  const [models, setModels] = useState<ModelCatalogEntry[]>([])
  const [modelsLoading, setModelsLoading] = useState(true)
  const [modelsError, setModelsError] = useState<string | null>(null)

  const [jobs, setJobs] = useState<Job[]>([])
  const [jobsLoading, setJobsLoading] = useState(true)
  const [jobsError, setJobsError] = useState<string | null>(null)

  const [benchmarks, setBenchmarks] = useState<BenchmarkRecord[]>([])
  const [benchmarkReport, setBenchmarkReport] =
    useState<BenchmarkReport | null>(null)
  const [benchmarksLoading, setBenchmarksLoading] = useState(true)
  const [benchmarksError, setBenchmarksError] = useState<string | null>(null)

  const [monitoring, setMonitoring] =
    useState<MonitoringDashboard | null>(null)
  const [monitoringLoading, setMonitoringLoading] = useState(true)
  const [monitoringError, setMonitoringError] = useState<string | null>(null)

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

  useEffect(() => {
    async function loadBenchmarks() {
      try {
        const [records, report] = await Promise.all([
          fetchBenchmarks(),
          fetchBenchmarkReport(),
        ])

        setBenchmarks(records)
        setBenchmarkReport(report)
      } catch (err) {
        setBenchmarksError(
          err instanceof Error ? err.message : 'Unable to load benchmarks.',
        )
      } finally {
        setBenchmarksLoading(false)
      }
    }

    void loadBenchmarks()
  }, [])

  useEffect(() => {
    async function loadMonitoring() {
      try {
        const data = await fetchMonitoringDashboard()
        setMonitoring(data)
      } catch (err) {
        setMonitoringError(
          err instanceof Error
            ? err.message
            : 'Unable to load monitoring data.',
        )
      } finally {
        setMonitoringLoading(false)
      }
    }

    void loadMonitoring()
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
        <p className="platform-name">Private LLM Platform</p>

        <nav className="navigation" aria-label="Platform navigation">
          <NavigationButton
            active={view === 'models'}
            onClick={() => setView('models')}
          >
            Models
          </NavigationButton>

          <NavigationButton
            active={view === 'jobs'}
            onClick={() => setView('jobs')}
          >
            Jobs
          </NavigationButton>

          <NavigationButton
            active={view === 'benchmarks'}
            onClick={() => setView('benchmarks')}
          >
            Benchmarks
          </NavigationButton>

          <NavigationButton
            active={view === 'monitoring'}
            onClick={() => setView('monitoring')}
          >
            Monitoring
          </NavigationButton>

          <NavigationButton
            active={view === 'chat'}
            onClick={() => setView('chat')}
          >
            Chat
          </NavigationButton>
        </nav>
      </header>

      {view === 'models' && (
        <ModelsView
          models={models}
          loading={modelsLoading}
          error={modelsError}
          enabledModels={enabledModels}
        />
      )}

      {view === 'jobs' && (
        <JobsView
          jobs={jobs}
          loading={jobsLoading}
          error={jobsError}
          counts={jobCounts}
        />
      )}

      {view === 'benchmarks' && (
        <BenchmarksView
          benchmarks={benchmarks}
          report={benchmarkReport}
          loading={benchmarksLoading}
          error={benchmarksError}
        />
      )}

      {view === 'monitoring' && (
        <MonitoringView
          monitoring={monitoring}
          loading={monitoringLoading}
          error={monitoringError}
        />
      )}

      {view === 'chat' && <ChatView />}
    </main>
  )
}

interface NavigationButtonProps {
  active: boolean
  onClick: () => void
  children: string
}

function NavigationButton({
  active,
  onClick,
  children,
}: NavigationButtonProps) {
  return (
    <button
      type="button"
      className={`nav-button ${active ? 'nav-active' : ''}`}
      onClick={onClick}
    >
      {children}
    </button>
  )
}

interface ModelsViewProps {
  models: ModelCatalogEntry[]
  loading: boolean
  error: string | null
  enabledModels: number
}

function ModelsView({
  models,
  loading,
  error,
  enabledModels,
}: ModelsViewProps) {
  return (
    <>
      <section className="hero">
        <div>
          <p className="eyebrow">Model catalog</p>
          <h1>Model Management</h1>
          <p className="hero-copy">
            View the models available on the platform and the inference engine
            assigned to each deployment.
          </p>
        </div>

        <SummaryCard label="Available models" value={models.length} />
      </section>

      <section className="content">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Catalog</p>
            <h2>Models</h2>
          </div>

          {!loading && !error && (
            <span className="status">{enabledModels} enabled</span>
          )}
        </div>

        {loading && <LoadingState message="Loading model catalog..." />}

        {error && (
          <ErrorState title="Unable to load models" message={error} />
        )}

        {!loading && !error && (
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
                        className={`engine-badge engine-${model.engine.toLowerCase()}`}
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
  )
}

interface JobsViewProps {
  jobs: Job[]
  loading: boolean
  error: string | null
  counts: Record<JobStatus, number>
}

function JobsView({
  jobs,
  loading,
  error,
  counts,
}: JobsViewProps) {
  return (
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

        <SummaryCard label="Tracked jobs" value={jobs.length} />
      </section>

      <section className="content">
        <div className="job-summary-grid">
          <MetricCard label="Pending" value={counts.pending} />
          <MetricCard label="Running" value={counts.running} />
          <MetricCard label="Completed" value={counts.completed} />
          <MetricCard label="Failed" value={counts.failed} />
        </div>

        <div className="section-heading jobs-heading">
          <div>
            <p className="eyebrow">Queue</p>
            <h2>Jobs</h2>
          </div>

          {!loading && !error && (
            <span className="status">{jobs.length} tracked</span>
          )}
        </div>

        {loading && <LoadingState message="Loading jobs..." />}

        {error && (
          <ErrorState title="Unable to load jobs" message={error} />
        )}

        {!loading && !error && jobs.length === 0 && (
          <EmptyState
            title="No jobs yet"
            message="Jobs submitted to the asynchronous processing pipeline will appear here."
          />
        )}

        {!loading && !error && jobs.length > 0 && (
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
  )
}

interface BenchmarksViewProps {
  benchmarks: BenchmarkRecord[]
  report: BenchmarkReport | null
  loading: boolean
  error: string | null
}

function BenchmarksView({
  benchmarks,
  report,
  loading,
  error,
}: BenchmarksViewProps) {
  const visibleBenchmarks = benchmarks.slice(-12)

  const latencyData: ChartDatum[] = visibleBenchmarks.map(
    (benchmark, index) => ({
      label: `Run ${index + 1}`,
      secondaryLabel: benchmark.engine,
      value: benchmark.latency_ms,
    }),
  )

  const throughputData: ChartDatum[] = visibleBenchmarks.map(
    (benchmark, index) => ({
      label: `Run ${index + 1}`,
      secondaryLabel: benchmark.engine,
      value: benchmark.throughput_tokens_per_second,
    }),
  )

  const engineAverages = useMemo(
    () => calculateEngineAverages(benchmarks),
    [benchmarks],
  )

  return (
    <>
      <section className="hero">
        <div>
          <p className="eyebrow">Performance analysis</p>
          <h1>Benchmark UI</h1>
          <p className="hero-copy">
            Compare LLM latency, token throughput, CPU, memory, and GPU
            utilization using benchmark measurements collected by the
            platform.
          </p>
        </div>

        <SummaryCard
          label="Benchmark runs"
          value={report?.benchmark_count ?? benchmarks.length}
        />
      </section>

      <section className="content">
        {loading && <LoadingState message="Loading benchmark results..." />}

        {error && (
          <ErrorState
            title="Unable to load benchmarks"
            message={error}
          />
        )}

        {!loading && !error && benchmarks.length === 0 && (
          <EmptyState
            title="No benchmark results yet"
            message="Benchmark executions will appear here once results are stored by the platform."
          />
        )}

        {!loading && !error && benchmarks.length > 0 && (
          <>
            {report && <BenchmarkSummary report={report} />}

            <div className="section-heading chart-section-heading">
              <div>
                <p className="eyebrow">Performance charts</p>
                <h2>Execution Comparison</h2>
              </div>

              <span className="status">
                Last {visibleBenchmarks.length} runs
              </span>
            </div>

            <div className="chart-grid">
              <BarChartCard
                title="Latency"
                description="Inference latency for each benchmark execution."
                unit="ms"
                data={latencyData}
              />

              <BarChartCard
                title="Throughput"
                description="Generated tokens per second for each execution."
                unit="tok/s"
                data={throughputData}
              />
            </div>

            <div className="section-heading chart-section-heading">
              <div>
                <p className="eyebrow">Engine comparison</p>
                <h2>Average Performance</h2>
              </div>

              <span className="status">
                {engineAverages.length} engine
                {engineAverages.length === 1 ? '' : 's'}
              </span>
            </div>

            <EngineComparisonChart engines={engineAverages} />

            <div className="section-heading chart-section-heading">
              <div>
                <p className="eyebrow">Resources</p>
                <h2>Benchmark Resource Usage</h2>
              </div>

              <span className="status">CPU / RAM / GPU</span>
            </div>

            <BenchmarkResourceChart benchmarks={visibleBenchmarks} />

            <div className="section-heading benchmark-heading">
              <div>
                <p className="eyebrow">Executions</p>
                <h2>Benchmark Results</h2>
              </div>

              <span className="status">
                {benchmarks.length} result
                {benchmarks.length === 1 ? '' : 's'}
              </span>
            </div>

            <div className="benchmark-grid">
              {benchmarks.map((benchmark) => (
                <BenchmarkCard
                  benchmark={benchmark}
                  key={benchmark.benchmark_id}
                />
              ))}
            </div>
          </>
        )}
      </section>
    </>
  )
}

interface MonitoringViewProps {
  monitoring: MonitoringDashboard | null
  loading: boolean
  error: string | null
}

function MonitoringView({
  monitoring,
  loading,
  error,
}: MonitoringViewProps) {
  const resources: ResourceDatum[] = monitoring
    ? [
        {
          label: 'CPU',
          value: monitoring.resources.cpu_percent,
        },
        {
          label: 'Memory',
          value: monitoring.resources.memory_percent,
        },
        {
          label: 'GPU',
          value: monitoring.resources.gpu_percent,
        },
      ]
    : []

  return (
    <>
      <section className="hero">
        <div>
          <p className="eyebrow">Platform observability</p>
          <h1>Monitoring UI</h1>
          <p className="hero-copy">
            Monitor system resource utilization and runtime status of the LLM
            inference engines.
          </p>
        </div>

        <SummaryCard
          label="Engines"
          value={monitoring?.engines.length ?? 0}
        />
      </section>

      <section className="content">
        {loading && (
          <LoadingState message="Loading monitoring data..." />
        )}

        {error && (
          <ErrorState
            title="Unable to load monitoring data"
            message={error}
          />
        )}

        {!loading && !error && monitoring && (
          <>
            <div className="section-heading">
              <div>
                <p className="eyebrow">Resources</p>
                <h2>System Usage</h2>
              </div>

              <span className="status">Live snapshot</span>
            </div>

            <div className="monitoring-resource-grid">
              <ResourceCard
                label="CPU"
                value={monitoring.resources.cpu_percent}
              />

              <ResourceCard
                label="Memory"
                value={monitoring.resources.memory_percent}
              />

              <ResourceCard
                label="GPU"
                value={monitoring.resources.gpu_percent}
              />
            </div>

            <div className="section-heading chart-section-heading">
              <div>
                <p className="eyebrow">Visualization</p>
                <h2>Resource Utilization</h2>
              </div>

              <span className="status">0–100%</span>
            </div>

            <MonitoringResourceChart resources={resources} />

            <div className="monitoring-note">
              <strong>Snapshot metrics</strong>
              <p>
                The dashboard API currently exposes the latest resource
                snapshot. Historical time-series monitoring remains available
                through the platform observability stack.
              </p>
            </div>

            <div className="section-heading monitoring-engine-heading">
              <div>
                <p className="eyebrow">Inference engines</p>
                <h2>Engine Status</h2>
              </div>

              <span className="status">
                {monitoring.engines.length} configured
              </span>
            </div>

            <div className="engine-status-grid">
              {monitoring.engines.map((engine) => (
                <EngineStatusCard
                  key={engine.engine}
                  engine={engine.engine}
                  status={engine.status}
                />
              ))}
            </div>
          </>
        )}
      </section>
    </>
  )
}

function BenchmarkSummary({
  report,
}: {
  report: BenchmarkReport
}) {
  return (
    <div className="benchmark-summary-grid">
      <MetricCard
        label="Avg latency"
        value={formatNumber(report.average_latency_ms)}
        unit="ms"
      />

      <MetricCard
        label="Avg throughput"
        value={formatNumber(
          report.average_throughput_tokens_per_second,
        )}
        unit="tok/s"
      />

      <MetricCard
        label="Avg CPU"
        value={formatNumber(report.average_cpu_percent)}
        unit="%"
      />

      <MetricCard
        label="Avg memory"
        value={formatNumber(report.average_memory_percent)}
        unit="%"
      />

      <MetricCard
        label="Avg GPU"
        value={
          report.average_gpu_percent === null
            ? 'N/A'
            : formatNumber(report.average_gpu_percent)
        }
        unit={report.average_gpu_percent === null ? undefined : '%'}
      />
    </div>
  )
}

function BarChartCard({
  title,
  description,
  unit,
  data,
}: {
  title: string
  description: string
  unit: string
  data: ChartDatum[]
}) {
  const maximum = Math.max(...data.map((item) => item.value), 1)

  return (
    <article className="chart-card">
      <div className="chart-card-header">
        <div>
          <p className="chart-kicker">Benchmark metric</p>
          <h3>{title}</h3>
        </div>

        <span className="chart-unit">{unit}</span>
      </div>

      <p className="chart-description">{description}</p>

      <div
        className="vertical-chart"
        aria-label={`${title} benchmark chart`}
      >
        {data.map((item, index) => {
          const height = Math.max((item.value / maximum) * 100, 3)

          return (
            <div
              className="vertical-chart-column"
              key={`${item.label}-${index}`}
            >
              <div className="vertical-chart-value">
                {formatNumber(item.value)}
              </div>

              <div className="vertical-chart-track">
                <div
                  className="vertical-chart-bar"
                  style={{ height: `${height}%` }}
                  title={`${item.label}: ${formatNumber(item.value)} ${unit}`}
                />
              </div>

              <div className="vertical-chart-label">
                <strong>{item.label}</strong>
                {item.secondaryLabel && (
                  <span>{item.secondaryLabel}</span>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </article>
  )
}

function EngineComparisonChart({
  engines,
}: {
  engines: EngineBenchmarkAverage[]
}) {
  if (engines.length === 0) {
    return (
      <EmptyState
        title="No engine comparison available"
        message="Benchmark multiple inference engines to generate comparison data."
      />
    )
  }

  return (
    <div className="engine-comparison-grid">
      {engines.map((engine) => (
        <article
          className="engine-comparison-card"
          key={engine.engine}
        >
          <div className="engine-comparison-header">
            <div>
              <p className="chart-kicker">Inference engine</p>
              <h3>{engine.engine.toUpperCase()}</h3>
            </div>

            <span
              className={`engine-badge engine-${engine.engine.toLowerCase()}`}
            >
              {engine.count} run{engine.count === 1 ? '' : 's'}
            </span>
          </div>

          <div className="engine-comparison-metrics">
            <ComparisonMetric
              label="Latency"
              value={engine.latency}
              unit="ms"
            />

            <ComparisonMetric
              label="Throughput"
              value={engine.throughput}
              unit="tok/s"
            />

            <ComparisonMetric
              label="CPU"
              value={engine.cpu}
              unit="%"
            />

            <ComparisonMetric
              label="Memory"
              value={engine.memory}
              unit="%"
            />

            <ComparisonMetric
              label="GPU"
              value={engine.gpu}
              unit="%"
            />
          </div>
        </article>
      ))}
    </div>
  )
}

function ComparisonMetric({
  label,
  value,
  unit,
}: {
  label: string
  value: number | null
  unit: string
}) {
  return (
    <div className="comparison-metric">
      <span>{label}</span>
      <strong>
        {value === null ? 'N/A' : formatNumber(value)}
        {value !== null && <small>{unit}</small>}
      </strong>
    </div>
  )
}

function BenchmarkResourceChart({
  benchmarks,
}: {
  benchmarks: BenchmarkRecord[]
}) {
  return (
    <article className="chart-card chart-card-wide">
      <div className="chart-card-header">
        <div>
          <p className="chart-kicker">Utilization per execution</p>
          <h3>CPU / Memory / GPU</h3>
        </div>

        <span className="chart-unit">%</span>
      </div>

      <div className="chart-legend">
        <span>
          <i className="legend-dot legend-cpu" />
          CPU
        </span>

        <span>
          <i className="legend-dot legend-memory" />
          Memory
        </span>

        <span>
          <i className="legend-dot legend-gpu" />
          GPU
        </span>
      </div>

      <div className="resource-execution-chart">
        {benchmarks.map((benchmark, index) => (
          <div
            className="resource-execution-row"
            key={benchmark.benchmark_id}
          >
            <div className="resource-execution-label">
              <strong>Run {index + 1}</strong>
              <span>{benchmark.engine}</span>
            </div>

            <div className="resource-execution-bars">
              <ResourceExecutionBar
                label="CPU"
                value={benchmark.resources.cpu_percent}
                className="resource-bar-cpu"
              />

              <ResourceExecutionBar
                label="Memory"
                value={benchmark.resources.memory_percent}
                className="resource-bar-memory"
              />

              <ResourceExecutionBar
                label="GPU"
                value={benchmark.resources.gpu_percent}
                className="resource-bar-gpu"
              />
            </div>
          </div>
        ))}
      </div>
    </article>
  )
}

function ResourceExecutionBar({
  label,
  value,
  className,
}: {
  label: string
  value: number | null
  className: string
}) {
  const normalized =
    value === null ? null : Math.max(0, Math.min(value, 100))

  return (
    <div className="resource-execution-bar-row">
      <span>{label}</span>

      <div className="resource-execution-track">
        {normalized !== null && (
          <div
            className={`resource-execution-fill ${className}`}
            style={{ width: `${normalized}%` }}
          />
        )}
      </div>

      <strong>
        {normalized === null ? 'N/A' : `${formatNumber(normalized)}%`}
      </strong>
    </div>
  )
}

function MonitoringResourceChart({
  resources,
}: {
  resources: ResourceDatum[]
}) {
  return (
    <article className="chart-card chart-card-wide">
      <div className="chart-card-header">
        <div>
          <p className="chart-kicker">System snapshot</p>
          <h3>Current Resource Utilization</h3>
        </div>

        <span className="chart-unit">%</span>
      </div>

      <div className="monitoring-chart">
        {resources.map((resource) => {
          const normalized =
            resource.value === null
              ? null
              : Math.max(0, Math.min(resource.value, 100))

          return (
            <div className="monitoring-chart-row" key={resource.label}>
              <div className="monitoring-chart-label">
                <strong>{resource.label}</strong>
                <span>
                  {normalized === null
                    ? 'Metric unavailable'
                    : getResourceState(normalized)}
                </span>
              </div>

              <div className="monitoring-chart-track">
                <div className="monitoring-chart-grid">
                  <span />
                  <span />
                  <span />
                  <span />
                </div>

                {normalized !== null && (
                  <div
                    className="monitoring-chart-fill"
                    style={{ width: `${normalized}%` }}
                  />
                )}
              </div>

              <div className="monitoring-chart-value">
                {normalized === null
                  ? 'N/A'
                  : `${formatNumber(normalized)}%`}
              </div>
            </div>
          )
        })}
      </div>

      <div className="chart-scale">
        <span>0%</span>
        <span>25%</span>
        <span>50%</span>
        <span>75%</span>
        <span>100%</span>
      </div>
    </article>
  )
}

function BenchmarkCard({
  benchmark,
}: {
  benchmark: BenchmarkRecord
}) {
  return (
    <article className="benchmark-card">
      <div className="benchmark-card-header">
        <div>
          <p className="benchmark-id">{benchmark.benchmark_id}</p>
          <h3>{benchmark.model_id}</h3>
        </div>

        <span
          className={`engine-badge engine-${benchmark.engine.toLowerCase()}`}
        >
          {benchmark.engine}
        </span>
      </div>

      <div className="benchmark-performance">
        <div>
          <span>Latency</span>
          <strong>{formatNumber(benchmark.latency_ms)} ms</strong>
        </div>

        <div>
          <span>Throughput</span>
          <strong>
            {formatNumber(
              benchmark.throughput_tokens_per_second,
            )}{' '}
            tok/s
          </strong>
        </div>
      </div>

      <dl className="benchmark-details">
        <div>
          <dt>Prompt</dt>
          <dd>{benchmark.prompt_id}</dd>
        </div>

        <div>
          <dt>Tokens generated</dt>
          <dd>{benchmark.tokens_generated.toLocaleString()}</dd>
        </div>

        <div>
          <dt>Duration</dt>
          <dd>{formatNumber(benchmark.duration_seconds)} s</dd>
        </div>

        <div>
          <dt>CPU</dt>
          <dd>{formatNumber(benchmark.resources.cpu_percent)}%</dd>
        </div>

        <div>
          <dt>Memory</dt>
          <dd>{formatNumber(benchmark.resources.memory_percent)}%</dd>
        </div>

        <div>
          <dt>Memory used</dt>
          <dd>{formatBytes(benchmark.resources.memory_used_bytes)}</dd>
        </div>

        <div>
          <dt>GPU</dt>
          <dd>
            {benchmark.resources.gpu_percent === null
              ? 'Not available'
              : `${formatNumber(benchmark.resources.gpu_percent)}%`}
          </dd>
        </div>

        <div>
          <dt>GPU memory</dt>
          <dd>
            {benchmark.resources.gpu_memory_used_bytes === null
              ? 'Not available'
              : formatBytes(
                  benchmark.resources.gpu_memory_used_bytes,
                )}
          </dd>
        </div>
      </dl>
    </article>
  )
}

function ResourceCard({
  label,
  value,
}: {
  label: string
  value: number | null
}) {
  const normalizedValue =
    value === null ? null : Math.max(0, Math.min(value, 100))

  return (
    <article className="resource-card">
      <div className="resource-card-header">
        <span>{label}</span>

        <strong>
          {normalizedValue === null
            ? 'N/A'
            : `${formatNumber(normalizedValue)}%`}
        </strong>
      </div>

      <div className="resource-track">
        <div
          className="resource-fill"
          style={{
            width:
              normalizedValue === null
                ? '0%'
                : `${normalizedValue}%`,
          }}
        />
      </div>

      <p>
        {normalizedValue === null
          ? 'Metric not available'
          : getResourceState(normalizedValue)}
      </p>
    </article>
  )
}

function EngineStatusCard({
  engine,
  status,
}: {
  engine: string
  status: string
}) {
  return (
    <article className="engine-status-card">
      <div>
        <p className="engine-status-label">Inference engine</p>
        <h3>{engine.toUpperCase()}</h3>
      </div>

      <span className={`runtime-status runtime-${status}`}>
        <span className="runtime-status-dot" />
        {formatRuntimeStatus(status)}
      </span>
    </article>
  )
}

function SummaryCard({
  label,
  value,
}: {
  label: string
  value: number
}) {
  return (
    <div className="summary-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function MetricCard({
  label,
  value,
  unit,
}: {
  label: string
  value: string | number
  unit?: string
}) {
  return (
    <article className="metric-card">
      <span>{label}</span>

      <strong>
        {value}
        {unit && <small>{unit}</small>}
      </strong>
    </article>
  )
}

function LoadingState({ message }: { message: string }) {
  return (
    <div className="state-card">
      <p>{message}</p>
    </div>
  )
}

function ErrorState({
  title,
  message,
}: {
  title: string
  message: string
}) {
  return (
    <div className="state-card error-card">
      <strong>{title}</strong>
      <p>{message}</p>
    </div>
  )
}

function EmptyState({
  title,
  message,
}: {
  title: string
  message: string
}) {
  return (
    <div className="state-card empty-state">
      <strong>{title}</strong>
      <p>{message}</p>
    </div>
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

function calculateEngineAverages(
  benchmarks: BenchmarkRecord[],
): EngineBenchmarkAverage[] {
  const engineGroups = new Map<string, BenchmarkRecord[]>()

  for (const benchmark of benchmarks) {
    const key = benchmark.engine.toLowerCase()
    const current = engineGroups.get(key) ?? []
    current.push(benchmark)
    engineGroups.set(key, current)
  }

  return Array.from(engineGroups.entries()).map(
    ([engine, records]) => {
      const gpuValues = records
        .map((record) => record.resources.gpu_percent)
        .filter((value): value is number => value !== null)

      return {
        engine,
        count: records.length,
        latency: average(
          records.map((record) => record.latency_ms),
        ),
        throughput: average(
          records.map(
            (record) => record.throughput_tokens_per_second,
          ),
        ),
        cpu: average(
          records.map((record) => record.resources.cpu_percent),
        ),
        memory: average(
          records.map((record) => record.resources.memory_percent),
        ),
        gpu: gpuValues.length > 0 ? average(gpuValues) : null,
      }
    },
  )
}

function average(values: number[]) {
  if (values.length === 0) {
    return 0
  }

  return values.reduce((total, value) => total + value, 0) / values.length
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

function formatRuntimeStatus(status: string) {
  return status
    .split(/[-_]/)
    .filter(Boolean)
    .map(
      (part) =>
        part.charAt(0).toUpperCase() + part.slice(1),
    )
    .join(' ')
}

function getResourceState(value: number) {
  if (value >= 85) {
    return 'High utilization'
  }

  if (value >= 60) {
    return 'Moderate utilization'
  }

  return 'Normal utilization'
}

function formatNumber(value: number) {
  return new Intl.NumberFormat('en-US', {
    maximumFractionDigits: 2,
  }).format(value)
}

function formatBytes(bytes: number) {
  if (bytes === 0) {
    return '0 B'
  }

  const units = ['B', 'KB', 'MB', 'GB', 'TB']

  const unitIndex = Math.min(
    Math.floor(Math.log(bytes) / Math.log(1024)),
    units.length - 1,
  )

  const value = bytes / 1024 ** unitIndex

  return `${formatNumber(value)} ${units[unitIndex]}`
}

export default App