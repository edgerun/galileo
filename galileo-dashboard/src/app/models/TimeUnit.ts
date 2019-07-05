export interface TimeUnit {
  id: TimeUnitKind,
  text: string
}

export enum TimeUnitKind {
  Second = "s",
  Minute = "min"
}

export const timeUnits: TimeUnit[] = [
  {
    id: TimeUnitKind.Second,
    text: 's'
  },
  {
    id: TimeUnitKind.Minute,
    text: 'min'
  }
];
