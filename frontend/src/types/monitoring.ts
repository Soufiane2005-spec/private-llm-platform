export interface MonitoringResources {
  cpu_percent: number
  memory_percent: number
  gpu_percent: number | null
}

export interface EngineStatus {
  engine: string
  status: string
}

export interface MonitoringDashboard {
  resources: MonitoringResources
  engines: EngineStatus[]
}