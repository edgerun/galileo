import {AfterContentInit, Component, EventEmitter, Inject, Input, OnInit, Output} from '@angular/core';
import * as D3CE from 'd3-curve-editor';
import {DOCUMENT} from "@angular/common";
import {CurveForm} from "../../models/ExperimentForm";
import * as d3 from 'd3';
import {debounce} from "ts-debounce";

@Component({
  selector: 'app-curve-editor',
  templateUrl: './curve-editor.component.html',
  styleUrls: ['./curve-editor.component.css']
})
export class CurveEditorComponent implements AfterContentInit {

  @Input()
  form: CurveForm;

  @Input()
  set duration(value: number) {
    if (value > 0) {
      this._duration = value;
      this.refreshValues();
    }
  }

  @Input()
  set interval(value: number) {
    if (value > 0) {
      this._interval = value;
      this.refreshValues();
    }
  }

  @Input()
  set maxRps(value: number) {
    if (value > 0) {
      this._maxRps = value;
      this.refreshValues();
    }
  }

  @Output()
  private formEmitter: EventEmitter<CurveForm> = new EventEmitter();

  private _duration: number;
  private _interval: number;
  private _initForm: CurveForm;

  get duration() {
    return this._duration;
  }


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

  _maxRps: number;

  editor;

  constructor(@Inject(DOCUMENT) private document) {
  }

  lines: D3CE.Line[] = [];

  ngAfterContentInit() {
    this._initForm = {
      points: [...this.form.points],
      curve: this.form.curve,
      ticks: [...this.form.ticks]
    };
    this.initEditor();
  }

  private initEditor() {
    const firstPoint = this._initForm.points[0];
    const endPoint = this._initForm.points[1];
    const curve = this.form.curve;
    const point = new D3CE.CurvePoint(firstPoint.x, firstPoint.y).isFixed(true);
    const line = new D3CE.Line("#47a", [
      point,
      new D3CE.CurvePoint(endPoint.x, endPoint.y).isFixed(true)
    ]);
    this.lines = [];
    this.lines.push(line);

    const container = this.document.getElementById('editor');
    container.innerHTML = '';
    container.setAttribute('height', "0");

    this.editor = new D3CE.CurveEditor(container, this.lines, getProps(this.duration, this.duration, curve));
    this.editor.active = {
      line,
      point
    };

    const debounced = debounce(() => {
      instance.editor.view.update();
      const points = instance.getCircles();
      instance.emitCalculatedPoints(points);
    }, 500);
    const instance = this;
    this.editor.eventListener.on('add change', function (_) {
      debounced();
    });

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
    const unsorted: Set<number> = new Set();
    const divider = this.duration / this.interval;
    const max = points[points.length - 1];
    const interval = Math.ceil(max.x / divider);
    const min = points[0];

    for (let i = 0; i <= max.x; i += interval) {
      unsorted.add(i);
    }

    const xs = [...unsorted].sort((n1, n2) => n1 - n2);
    const ys: number[] = [];

    this.removeTicks();
    const path = this.document.querySelector('path');
    for (let x of xs) {
      let y = this.findYForX(x, path, 0);
      this.drawTick(min.x + x, y, min.y);
      y = Math.ceil(this.maxRps * (1 - (y / min.y)));
      ys.push(y);
    }

    this.form = {
      ...this.form,
      points: points,
      ticks: ys
    };

    this.formEmitter.emit(this.form);
  }


  private removeTicks() {
    d3.selectAll('.value-line').remove();
  }

  private drawTick(x, y1, y2) {
    const container = d3.select('g');

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

  reset() {
    if (this.editor) {
      this.initEditor();
    }
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
    fixedAxis: D3CE.Axes.list[1]
  };
}
