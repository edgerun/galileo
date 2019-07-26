import {Component, EventEmitter, Input, OnInit} from '@angular/core';
import {FormBuilder, FormGroup, Validators} from "@angular/forms";
import {CurveForm} from "../../models/ExperimentForm";
import {convertToSeconds, TimeUnit, timeUnits} from "../../models/TimeUnit";
import * as d3 from 'd3';
import {ExperimentConfiguration, WorkloadConfiguration} from "../../models/ExperimentConfiguration";
import {Service} from "../../models/Service";

@Component({
  selector: 'app-workload-form',
  templateUrl: './workload-form.component.html',
  styleUrls: ['./workload-form.component.css']
})
export class WorkloadFormComponent implements OnInit {


  private _initCurveForm: CurveForm;
  form: FormGroup;
  calculatedForm: CurveForm;
  workloadSubmission: EventEmitter<WorkloadConfiguration> = new EventEmitter<WorkloadConfiguration>();

  @Input()
  duration: number;

  @Input()
  maxRps: number;

  @Input()
  interval: number;

  @Input()
  curveForm: CurveForm;

  @Input()
  services: Service[];


  constructor(private fb: FormBuilder) {
    this.form = this.fb.group({
      service: [{name: ""}, Validators.required],
      numberOfClients: [3, [Validators.required, Validators.pattern('[0-9]*')]]
    });
  }

  ngOnInit(): void {
    this._initCurveForm = {
      curve: this.curveForm.curve,
      ticks: this.curveForm.ticks,
      points: this.curveForm.points
    }
  }

  handleCurveForm(form: CurveForm) {
    this.calculatedForm = form;
    const workload: WorkloadConfiguration = {
      service: this.form.get('service').value.name,
      ticks: this.calculatedForm.ticks,
      clients_per_host: this.form.get('numberOfClients').value
    };

    this.workloadSubmission.emit(workload);
  }

  reset() {
    this.curveForm = this._initCurveForm;
  }

}
