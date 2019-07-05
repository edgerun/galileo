import {AfterContentInit, Component, ElementRef, Inject, Input, OnInit, ViewChild} from '@angular/core';
import * as D3CE from 'd3-curve-editor';
import {DOCUMENT} from "@angular/common";
import * as d3 from 'd3';

@Component({
  selector: 'app-curve-editor',
  templateUrl: './curve-editor.component.html',
  styleUrls: ['./curve-editor.component.css']
})
export class CurveEditorComponent implements OnInit, AfterContentInit {

  @Input()
  set duration(value: number) {
    this._duration = value;
    this.reset();
  }

  _duration: number;

  get duration() {
    return this._duration;
  }

  @Input()
  maxRps: number;

  editor;

  constructor(@Inject(DOCUMENT) private document) {
  }

  lines: D3CE.Line[] = [];

  ngAfterContentInit() {
    this.initEditor();
  }

  private initEditor() {
    const point = new D3CE.CurvePoint(0, 0).isFixed(true);
    const line = new D3CE.Line("#47a", [
      point,
      new D3CE.CurvePoint(this.duration, 0).isFixed(true)
    ]);
    this.lines.push(line);

    const container = this.document.getElementById('editor');


    const properties = {
      range: {
        x: new D3CE.Range(0, this.duration),
        y: new D3CE.Range(0, this.duration),
        z: new D3CE.Range(0, this.duration),
      },
      curve: d3.curveStep,
      stretch: true
    };

    this.editor = new D3CE.CurveEditor(container, this.lines, properties);
    this.editor.active = {
      line,
      point
    };

  }

  ngOnInit(): void {
  }

  reset() {
    if (this.editor) {
      const point = new D3CE.CurvePoint(0, 0).isFixed(true);
      const line = new D3CE.Line("#47a", [
        point,
        new D3CE.CurvePoint(this.duration, 0).isFixed(true)
      ]);
      this.lines = [];
      this.lines.push(line);
      this.editor.lines = this.lines;

      this.editor.active = {
        line,
        point
      };

      const properties = {
        range: {
          x: new D3CE.Range(0, this.duration),
          y: new D3CE.Range(0, this.duration),
          z: new D3CE.Range(0, this.duration),
        },
        curve: d3.curveStep,
        stretch: true
      };

      const container = this.document.getElementById('editor');
      container.innerHTML = '';
      container.setAttribute('height',"0");

      this.editor = new D3CE.CurveEditor(container, this.lines, properties);
      this.editor.active = {
        line,
        point
      };


      this.editor.view.update();
    }
  }
}
