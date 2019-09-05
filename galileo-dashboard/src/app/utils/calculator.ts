import {convertTimeToSeconds, Time} from '../models/TimeUnit';

export function findYForX(x, path, error = 0.01): number {
  let lengthEnd = path.getTotalLength();
  let lengthStart = 0;
  let point = path.getPointAtLength((lengthEnd + lengthStart) / 2); // get the middle point
  const bisectionIterationsMax = 50;
  let bisectionIterations = 0;


  while (x < point.x - error || x > point.x) {
    // get the middle point
    point = path.getPointAtLength((lengthEnd + lengthStart) / 2);

    if (x < point.x) {
      lengthEnd = (lengthStart + lengthEnd) / 2;
    } else {
      lengthStart = (lengthStart + lengthEnd) / 2;
    }

    // Increase iteration
    if (bisectionIterationsMax < ++bisectionIterations) {
      break;
    }
  }
  return point.y;
}

export function calculateNumberOfTicks(duration: Time, interval: Time) {
  const durationSeconds = convertTimeToSeconds(duration);
  const intervalSeconds = convertTimeToSeconds(interval);
  return Math.ceil(durationSeconds / intervalSeconds);
}

export function round(value, precision) {
  const multiplier = Math.pow(10, precision || 0);
  return Math.round(value * multiplier) / multiplier;
}

export function calculateValues(duration: Time, interval: Time, maxRps: number, points: { x: number, y: number }[], path): number[] {
  const max = points[points.length - 1];
  const min = points[0]; // we assume min.x = 0

  const n = calculateNumberOfTicks(duration, interval);
  const intervalScreen = max.x / n; // distance between ticks in screen space
  const fn: Array<number> = new Array<number>(n); // y values in function space


  for (let i = 0; i < n; i++) {
    const xs = i * intervalScreen; // x in screen space
    const ys = findYForX(xs, path, 0); // y in screen space

    // calculate y in function space
    let yf = Math.ceil(maxRps * (1 - (ys / min.y)));
    if (yf === -Infinity) {
      yf = 0;
    }
    fn[i] = yf;

  }

  return fn;
}
