export interface MonitoringResources {
  cpu_percent: number
  memory_percent: number
  gpu_percent: number | null
}

export interface EngineStatus {
  engine: string
  status: string
}

export interface PodStatus {
  namespace: string
  name: string
  ready: boolean
}

export interface MonitoringAlert {
  name: string
  severity: string | null
  state: string
}

export interface MonitoringDashboard {
  resources: MonitoringResources
  engines: EngineStatus[]
  pods: PodStatus[]
  alerts: MonitoringAlert[]
}
