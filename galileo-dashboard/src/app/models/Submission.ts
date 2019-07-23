import {ExperimentConfiguration} from "./ExperimentConfiguration";

export interface Submission {
  experiment?: {name?: string, creator?: string},
  configuration: ExperimentConfiguration
}
