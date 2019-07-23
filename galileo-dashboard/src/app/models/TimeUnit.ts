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

export function convertToSeconds(value: number, unit: TimeUnit): number {
  switch (unit.id) {
    case TimeUnitKind.Minute:
      return value * 60;
    case TimeUnitKind.Second:
      return value;
  }
}
