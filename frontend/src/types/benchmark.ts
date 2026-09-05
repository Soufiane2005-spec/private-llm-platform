export interface BenchmarkResources {
  cpu_percent: number
  memory_percent: number
  memory_used_bytes: number
  gpu_percent: number | null
  gpu_memory_used_bytes: number | null
}

export interface BenchmarkRecord {
  benchmark_id: string
  model_id: string
  prompt_id: string
  engine: string
  latency_ms: number
  ttft_ms: number
  tokens_generated: number
  duration_seconds: number
  throughput_tokens_per_second: number
  resources: BenchmarkResources
}

export interface BenchmarkReport {
  benchmark_count: number
  average_latency_ms: number
  average_throughput_tokens_per_second: number
  average_cpu_percent: number
  average_memory_percent: number
  average_gpu_percent: number | null
}

export interface BenchmarkRunResponse {
  job: {
    job_id: string
    status: string
    error: string | null
  }
  records: BenchmarkRecord[]
  recommendation: string | null
}
