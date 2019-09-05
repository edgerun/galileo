import {CurveForm} from './ExperimentForm';
import {LoadBalancingPolicy} from './LoadBalancingPolicy';

export interface ExperimentConfiguration {
  duration: string;
  interval: string;
  workloads: WorkloadConfiguration[];
  policy?: LoadBalancingPolicy;
}

export interface WorkloadConfiguration {
  service: string;
  client: string;
  ticks: number[];
  clients_per_host: number;
  arrival_pattern: string;
  maxRps?: number;
  curve?: CurveForm;
}
