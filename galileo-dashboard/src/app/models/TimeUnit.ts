export class Time {
  constructor(public value: number, public kind: TimeUnitKind) {
  }

  equals(other: Time): boolean {
    return other.value == this.value && other.kind == this.kind;
  }
}

export enum TimeUnitKind {
  Second = "s",
  Minute = "min"
}

export const timeUnits: TimeUnitKind[] = [
  TimeUnitKind.Second,
  TimeUnitKind.Minute
];

export function convertToSeconds(value: number, unit: TimeUnitKind): number {
  switch (unit) {
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
    default:
      console.error("Should not happen. Time was: " + time.kind + " " + time.value)
  }
}

export function convertSecondsToTime(time: string): Time {
  const seconds = parseInt(time.replace('s', ''));
  return new Time(seconds, TimeUnitKind.Second);
}



