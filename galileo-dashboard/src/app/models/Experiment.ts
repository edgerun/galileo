export interface Experiment {
  id: string;
  name?: string;
  creator?: string;
  start?: number;
  end?: number;
  created?: number;
  status: string;
}
