import {Time, TimeUnitKind} from './TimeUnit';
import {WorkloadConfiguration} from './ExperimentConfiguration';
import {LoadBalancingPolicy} from './LoadBalancingPolicy';
import {Service} from './Service';


export interface ExperimentForm {
  experiment: { name?: string, creator?: string };
  workloads: Map<string, WorkloadConfiguration>;
  policy?: LoadBalancingPolicy;
  duration: Time;
  interval: Time;
}

export interface UnvalidatedExperimentForm {
  id?: string;
  name?: string;
  creator?: string;
  interval?: TimeUnitKind;
  duration?: TimeUnitKind;
  service?: Service;
}

export interface CurveForm {
  points: Point[];
  interpolation: CurveKind;
  ticks?: number[];
}

export enum CurveKind {
  Basis = 'Basis',
  Linear = 'Linear',
  Step = 'Step',
  CatMull = 'CatMullRom'
}

export interface Point {
  x: number;
  y: number;
}
