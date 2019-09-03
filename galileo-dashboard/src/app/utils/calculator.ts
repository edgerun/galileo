import {convertTimeToSeconds, Time} from "../models/TimeUnit";

export function findYForX(x, path, error = 0.01): number {
  var length_end = path.getTotalLength()
    , length_start = 0
    , point = path.getPointAtLength((length_end + length_start) / 2) // get the middle point
    , bisection_iterations_max = 50
    , bisection_iterations = 0;


  while (x < point.x - error || x > point.x) {
    // get the middle point
    point = path.getPointAtLength((length_end + length_start) / 2);

    if (x < point.x) {
      length_end = (length_start + length_end) / 2
    } else {
      length_start = (length_start + length_end) / 2
    }

    // Increase iteration
    if (bisection_iterations_max < ++bisection_iterations)
      break;
  }
  return point.y
}

export function calculateNumberOfTicks(duration: Time, interval: Time) {
  const durationSeconds = convertTimeToSeconds(duration);
  const intervalSeconds = convertTimeToSeconds(interval);
  return Math.ceil(durationSeconds / intervalSeconds);
}

export function calculateValues(duration: Time, interval: Time, maxRps: number, points: { x: number, y: number }[], path): number[] {
  const max = points[points.length - 1];
  const min = points[0]; // we assume min.x = 0

  const n = calculateNumberOfTicks(duration, interval);
  const interval_screen = max.x / n; // distance between ticks in screen space
  const fn: Array<number> = new Array<number>(n); // y values in function space


  for (let i = 0; i < n; i++) {
    let xs = i * interval_screen; // x in screen space
    let ys = findYForX(xs, path, 0); // y in screen space

    // calculate y in function space
    let yf = Math.ceil(maxRps * (1 - (ys / min.y)));
    if (yf === -Infinity) {
      yf = 0
    }
    fn[i] = yf;

  }

  return fn;
}
