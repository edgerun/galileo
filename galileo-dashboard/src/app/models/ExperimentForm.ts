import {TimeUnit} from "./TimeUnit";
import {Service} from "./Service";

export interface ExperimentForm {
  id: string,
  name: string,
  creator: string,
  interval: TimeUnit,
  duration: TimeUnit,
  service: Service,
}

export interface UnvalidatedExperimentForm {
  id?: string,
  name?: string,
  creator?: string,
  interval?: TimeUnit,
  duration?: TimeUnit,
  service?: Service,
}

export interface CurveForm {
  points: Point[],
  curve: CurveKind
}

export enum CurveKind {
  Basis,
  Linear,
  Step
}

export interface Point {
  x: number,
  y: number
}
