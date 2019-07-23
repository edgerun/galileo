import {Component, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {TimeUnit, TimeUnitKind, timeUnits} from "../../models/TimeUnit";
import {CurveForm, ExperimentForm} from "../../models/ExperimentForm";
import {FormBuilder, FormGroup, Validators} from "@angular/forms";
import {noWhitespaceValidator} from "../../utils/validators";
import {Service} from "../../models/Service";
import * as d3 from 'd3';

@Component({
  selector: 'app-experiment-form',
  templateUrl: './experiment-form.component.html',
  styleUrls: ['./experiment-form.component.css']
})
export class ExperimentFormComponent implements OnInit {

  @Input()
  services: Service[];

  @Output()
  add = new EventEmitter<ExperimentForm>();

  form: FormGroup;
  curveForm: CurveForm;

  constructor(private fb: FormBuilder) {
  }

  ngOnInit() {
    this.form = this.fb.group({
      name: ['', [Validators.required, noWhitespaceValidator]],
      creator: ['', [Validators.required, noWhitespaceValidator]],
      interval: [10, [Validators.required, Validators.pattern('[0-9]*')]],
      intervalUnit: [timeUnits[0], Validators.required],
      duration: [100, [Validators.required, Validators.pattern('[0-9]*')]],
      durationUnit: [timeUnits[0], Validators.required],
      service: [undefined, Validators.required],
      maxRps: [1000, [Validators.required, Validators.pattern('[0-9]*')]],
      numberOfClients: [3, [Validators.required, Validators.pattern('[0-9]*')]]
    });

    this.curveForm = {
      points: [{x: 0, y: 0}, {x: this.form.get('duration').value, y: 0}],
      curve: d3.curveBasis
    };

  }

  submit() {
    console.log(this.form.value)
  }

  handleValues(values: number[]) {
    console.log(values);
  }
}
