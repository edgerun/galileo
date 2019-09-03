export interface ExperimentConfiguration {
  duration: string,
  interval: string
  workloads: WorkloadConfiguration[]
}

export interface WorkloadConfiguration {
  service: string,
  client: string,
  ticks: number[],
  clients_per_host: number,
  arrival_pattern: string
}
