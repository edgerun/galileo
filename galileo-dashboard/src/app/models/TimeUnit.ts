export interface TimeUnit {
  id: TimeUnitKind,
  text: string
}

export class Time {
  constructor(public value: number, public kind: TimeUnitKind) {}

  equals(other: Time): boolean {
    return other.value == this.value && other.kind == this.kind;
  }
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

export function convertTimeToSeconds(time: Time): number {
    switch (time.kind) {
    case TimeUnitKind.Minute:
      return time.value * 60;
    case TimeUnitKind.Second:
      return time.value;
  }
}

