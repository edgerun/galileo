import {
  AfterContentInit,
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  Inject,
  Input,
  OnDestroy,
  Output
} from '@angular/core';
import * as D3CE from 'd3-curve-editor';
import {DOCUMENT} from "@angular/common";
import {CurveForm, CurveKind, Point} from "../../models/ExperimentForm";
import * as d3 from 'd3';
import {debounce} from "ts-debounce";
import {convertTimeToSeconds, Time} from "../../models/TimeUnit";
import {findYForX, round} from "../../utils/calculator";

@Component({
  selector: 'app-curve-editor',
  templateUrl: './curve-editor.component.html',
  styleUrls: ['./curve-editor.component.css'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class CurveEditorComponent implements AfterContentInit, AfterViewInit, OnDestroy {

  private oldRpsMax: number;
  private oldDuration: number;
  private observer: MutationObserver;
  private _duration: Time;
  private _interval: Time;
  private _form: CurveForm;
  private _maxRps: number;
  editor;

  @Input()
  id: string;

  @Input()
  set form(value: CurveForm) {
    console.info('set form')
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
    if ((time.value > 0 && (!this.duration || !this.duration.equals(time)))) {
      if (!this.duration) {
        this.oldDuration = getMaxValue();
      } else {
        this.oldDuration = this.duration.value;
      }

      this._duration = time;
      this.renameDurationTicks();
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
      this.oldRpsMax = this.maxRps;
      this._maxRps = value;
      this.renameRpsTicks();
      this.debouncedRefresh();
    }
  }

  @Output()
  private formEmitter: EventEmitter<CurveForm> = new EventEmitter();

  get duration() {
    return this._duration;
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


  ngAfterContentInit() {
    this.initEditor();
  }

  ngAfterViewInit(): void {
    this.initEditor();
  }

  ngOnDestroy(): void {
    if (this.observer) {
      this.observer.disconnect();
      this.observer = undefined;
    }
  }

  private initEditor() {
    if (this.observer) {
      this.observer.disconnect();
      this.observer = undefined;
    }

    if (this.document.getElementById(this.id) != null) {
      const firstPoint = this.form.points[0];
      const endPoint = this.form.points[this.form.points.length - 1];
      const curve = this.getCurve();
      const point = new D3CE.CurvePoint(firstPoint.x, firstPoint.y).isFixed(true);
      const points = [];

      for (let i = 1; i < this.form.points.length - 1; i++) {
        points.push(new D3CE.CurvePoint(this.form.points[i].x, this.form.points[i].y))
      }

      const line = new D3CE.Line("#47a", [
        point,
        ...points,
        new D3CE.CurvePoint(endPoint.x, endPoint.y).isFixed(true)
      ]);

      this.lines = [];
      this.lines.push(line);

      const container = this.document.getElementById(this.id);
      container.innerHTML = '';
      container.setAttribute('height', "0");

      this.editor = new D3CE.CurveEditor(container, this.lines, getProps(curve));

      this.editor.active = {
        line,
        point
      };
      const instance = this;

      const debounced = debounce(() => {
        instance.editor.view.update();
        const points = instance.getCircles();
        instance.formEmitter.emit({points, interpolation: this.form.interpolation});
      }, 500);

      this.editor.eventListener.on('add change', function (_) {
        debounced();
      });
      this.formEmitter.emit({points: this.getCircles(), interpolation: this.form.interpolation});
      this.initMutationObserver();
    }
  }

  private getCurve() {
    switch (this.form.interpolation) {
      case CurveKind.Basis:
        return d3.curveBasis;
      case CurveKind.Linear:
        return d3.curveLinear;
      case CurveKind.Step:
        return d3.curveStep;
      case CurveKind.CatMull:
        return d3.curveCatmullRom
    }
  }

  private initMutationObserver() {
    const container = this.document.getElementById(this.id);
    const node = container.querySelector('g');
    this.observer = new MutationObserver((mutations) => {
      this.oldRpsMax = getMaxValue();
      this.oldDuration = getMaxValue();
      this.renameRpsTicks();
      this.renameDurationTicks();
    });

    this.observer.observe(node, {
      attributes: true,
    });

    this.oldRpsMax = getMaxValue();
    this.oldDuration = getMaxValue();
    this.renameRpsTicks();
    this.renameDurationTicks();
  }

  private renameRpsTicks() {
    this.renameAxis('end', this.maxRps, this.oldRpsMax);
  }

  private renameDurationTicks() {
    this.renameAxis('middle', this.duration.value, this.oldDuration, this.duration.kind);
  }

  private renameAxis(anchor: string, max: number, old: number, unit: string = "") {
    const textNodes = [...this.document.querySelectorAll(`[id="${this.id}"] g[text-anchor="${anchor}"] g text`)];
    const fn = (val: number) => val * (max / old);
    textNodes.forEach(node => {
      const number = +(node.innerHTML.split(" ")[0]);
      let tick = Math.ceil(fn(number));
      if (Math.abs(fn(number)) < 5) {
        tick = round(fn(number), 2);
      }
      node.innerHTML = tick + " " + unit;
    });
  }

  private getCircles() {
    const circles = [...this.document.querySelectorAll(`[id="${this.id}"] circle`)];
    return circles.map(c => {
      return {
        x: c.getAttribute('cx'),
        y: c.getAttribute('cy')
      }
    });
  }

  private debouncedRefresh = debounce(this.refreshValues, 500);

  private refreshValues() {
    if (this.editor) {
      const points = this.getCircles();
      this.formEmitter.emit({points, interpolation: this.form.interpolation});
    }
  }


}

function getProps(curve) {
  return {
    range: getRange(),
    curve: curve,
    stretch: true,
    fixedAxis: D3CE.Axes.list[1],
    margin: 60
  };
}

function getMaxValue() {
  return 100;
}

function getRange() {
  return {
    x: new D3CE.Range(0, getMaxValue()),
    y: new D3CE.Range(0, getMaxValue()),
    z: new D3CE.Range(0, 1),
  }
}
