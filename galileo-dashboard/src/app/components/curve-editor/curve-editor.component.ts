import {
  AfterContentInit,
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  Inject,
  Input, OnDestroy,
  Output
} from '@angular/core';
import * as D3CE from 'd3-curve-editor';
import {DOCUMENT} from "@angular/common";
import {CurveForm} from "../../models/ExperimentForm";
import * as d3 from 'd3';
import {debounce} from "ts-debounce";
import {convertTimeToSeconds, Time} from "../../models/TimeUnit";

@Component({
  selector: 'app-curve-editor',
  templateUrl: './curve-editor.component.html',
  styleUrls: ['./curve-editor.component.css'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class CurveEditorComponent implements AfterContentInit, AfterViewInit, OnDestroy {

  @Input()
  id: string;

  @Input()
  set form(value: CurveForm) {
    if (!this.form) {
      this._form = value;
    }

    if (this.editor) {
      this._form = value;
      this.initEditor();
      this.debouncedRefresh();
    }

  }

  get form() {
    return this._form;
  }

  @Input()
  set duration(time: Time) {
    if (!this.duration || (time.value > 0 && !this.duration.equals(time))) {
      this._duration = time;
      this.debouncedRefresh();
    }
  }

  @Input()
  set interval(time: Time) {
    if (!this.interval || (time.value > 0 && !this.interval.equals(time))) {
      this._interval = time;
      this.debouncedRefresh();
    }
  }

  @Input()
  set maxRps(value: number) {
    if (value > 0 && this.maxRps != value) {
      this._maxRps = value;
      this.debouncedRefresh();
    }
  }

  @Output()
  private formEmitter: EventEmitter<CurveForm> = new EventEmitter();

  private _duration: Time;
  private _interval: Time;
  private _form: CurveForm;
  private _maxRps: number;
  editor;

  get duration() {
    return this._duration;
  }

  private debouncedRefresh = debounce(this.refreshValues, 500);

  private refreshValues() {
    if (this.editor) {
      const points = this.getCircles();
      this.emitCalculatedPoints(points);
    }
  }


  get maxRps(): number {
    return this._maxRps;
  }

  get interval() {
    return this._interval;
  }


  constructor(@Inject(DOCUMENT) private document) {
  }

  lines: D3CE.Line[] = [];
  private oldRpsPoints: number[] = [];
  private oldDurationPoints: number[] = [];
  private timer: number = -1;

  ngAfterContentInit() {
    this.initEditor();
    this.timer = setInterval(() => {
      this.renameRpsTicks();
      this.renameDurationTicks();
    }, 50);
  }

  ngOnDestroy(): void {
    if (this.timer != -1) {
      clearInterval(this.timer);
      this.timer = -1;
    }
  }

  ngAfterViewInit(): void {
    this.initEditor();
  }


  private renameRpsTicks() {
    const result = this.tryRenameAxis('end', this.oldRpsPoints, this.maxRps);
    if (result[0]) {
      this.oldRpsPoints = result[1];
    }
  }

  private tryRenameAxis(anchor: string, oldPoints: number[], max: number): [boolean, number[]] {
    const textNodes = [...this.document.querySelectorAll(`[id="${this.id}"] g[text-anchor="${anchor}"] g text`)];
    let equals = true;
    if (textNodes.length > 0) {
      for (let i = 0; i < textNodes.length; i++) {
        if (i < oldPoints.length) {
          equals = equals && (oldPoints[i] === +textNodes[i].innerHTML);
        } else {
          equals = false;
        }
      }
      if (equals) return [false, []];
    }
    return this.renameAxis(anchor, max);
  }

  private renameAxis(anchor: string, max: number): [boolean, number[]] {
    const textNodes = [...this.document.querySelectorAll(`[id="${this.id}"] g[text-anchor="${anchor}"] g text`)];
    this.renameNodes(max, textNodes);
    return [true, textNodes.map(t => +t.innerHTML)];
  }

  private renameNodes(max: number, textNodes) {
    const fn = (val: number) => val * (max / 100);
    textNodes.forEach(node => {
      node.innerHTML = fn(+node.innerHTML);
    });
  }

  private renameDurationTicks() {
    const result = this.tryRenameAxis('middle', this.oldDurationPoints, this.duration.value);
    if (result[0]) {
      this.oldDurationPoints = result[1];
    }
  }

  private initEditor() {
    if (this.document.getElementById(this.id) != null) {
      const firstPoint = this.form.points[0];
      const endPoint = this.form.points[1];
      const curve = this.form.curve;
      const point = new D3CE.CurvePoint(firstPoint.x, firstPoint.y).isFixed(true);
      const line = new D3CE.Line("#47a", [
        point,
        new D3CE.CurvePoint(endPoint.x, endPoint.y).isFixed(true)
      ]);
      this.lines = [];
      this.lines.push(line);

      const container = this.document.getElementById(this.id);

      container.innerHTML = '';
      container.setAttribute('height', "0");

      this.editor = new D3CE.CurveEditor(container, this.lines, getProps(this.duration, this.duration, curve));
      this.editor.active = {
        line,
        point
      };
      const instance = this;

      const debounced = debounce(() => {
        instance.editor.view.update();
        const points = instance.getCircles();
        instance.emitCalculatedPoints(points);
      }, 500);

      this.editor.eventListener.on('add change', function (_) {
        debounced();
      });
      this.emitCalculatedPoints(this.form.points);
    }
  }

  private getCircles() {
    const circles = [...this.document.querySelectorAll('circle')];
    return circles.map(c => {
      return {
        x: c.getAttribute('cx'),
        y: c.getAttribute('cy')
      }
    });
  }

  private emitCalculatedPoints(points: { x: number, y: number }[]) {
    const max = points[points.length - 1];
    const min = points[0]; // we assume min.x = 0

    const durationSeconds = convertTimeToSeconds(this.duration);
    const intervalSeconds = convertTimeToSeconds(this.interval);
    const n = Math.ceil(durationSeconds / intervalSeconds);
    console.info(n);
    const interval_screen = max.x / n; // distance between ticks in screen space
    const fn: Array<number> = new Array<number>(n); // y values in function space

    const svg = this.document.getElementById(`${this.id}`);
    const path = svg.querySelector(`path`);
    this.removeTicks();

    for (let i = 0; i < n; i++) {
      let xs = i * interval_screen; // x in screen space
      let ys = this.findYForX(xs, path, 0); // y in screen space

      // calculate y in function space
      let yf = Math.ceil(this.maxRps * (1 - (ys / min.y)));
      if (yf === -Infinity) {
        yf = 0
      }
      fn[i] = yf;

      this.drawTick(xs, ys, min.y);
    }

    this._form = {
      ...this.form,
      points: points,
      ticks: fn
    };

    this.formEmitter.emit(this.form);
  }


  private removeTicks() {
    d3.selectAll(`[id="${this.id}"] .value-line`).remove();
  }

  private drawTick(x, y1, y2) {
    const container = d3.select(`[id="${this.id}"] g`);
    container.append('line')
      .attr('x1', x)
      .attr('y1', y1)
      .attr('x2', x)
      .attr('y2', y2)
      .attr('class', 'value-line')
      .attr('stroke', 'red')
      .attr('stroke-width', '5');
  }

  private findYForX(x, path, error = 0.01): number {
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


  private fixRpsTicks() {

    // const container = [...this.document.querySelectorAll(`[id="${this.id}"] g[text-anchor="end"] g`)];
    // console.info(container);
    // const size = container.length;
    // const interval = this.maxRps / size;
    // this.document.querySelector(`[id="${this.id}"] g[text-anchor="end"]`).innerHTML = "";
    // for (let i = 0; i <= this.maxRps; i += interval) {
    //   if (container[i]) {
    //     container[i].innerHTML = i;
    //     console.info(container[i]);
    //     this.document.querySelector(`[id="${this.id}"] g[text-anchor="end"]`).appendChild(container[i]);
    //   }
    // }
    //
    // console.log(container);
  }
}

function getProps(duration, maxRps, curve) {
  return {
    range: {
      x: new D3CE.Range(0, 100),
      y: new D3CE.Range(0, 100),
      z: new D3CE.Range(0, 1),
    },
    curve: curve,
    stretch: true,
    fixedAxis: D3CE.Axes.list[1],
    margin: 40
  };
}
