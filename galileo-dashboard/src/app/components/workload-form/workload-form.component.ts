import {Component, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {FormBuilder, FormGroup, Validators} from "@angular/forms";
import {CurveForm} from "../../models/ExperimentForm";
import {convertToSeconds, Time, TimeUnit, timeUnits} from "../../models/TimeUnit";
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

  @Output()
  workloadSubmission: EventEmitter<WorkloadConfiguration> = new EventEmitter<WorkloadConfiguration>();

  @Output()
  removeWorkload = new EventEmitter<void>();

  @Input()
  duration: Time;

  @Input()
  id: string;

  @Input()
  interval: Time;

  @Input()
  curveForm: CurveForm;

  @Input()
  services: Service[];
  errorMessage: string;


  constructor(private fb: FormBuilder) {
    this.form = this.fb.group({
      maxRps: [1000, [Validators.required, Validators.pattern('[0-9]*')]],
      service: [undefined, Validators.required],
      numberOfClients: [3, [Validators.required, Validators.pattern('[0-9]*')]]
    });

    this.form.get('service').valueChanges.subscribe(val => {
      this.handleCurveForm(this.calculatedForm);
    });

    this.form.get('numberOfClients').valueChanges.subscribe(val => {
      this.handleCurveForm(this.calculatedForm);
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



    function getService(value: Service) {
      if (value) {
        return value.name;
      } else {
        return "";
      }
    }

    const workload: WorkloadConfiguration = {
      service: getService(this.form.get('service').value),
      ticks: this.calculatedForm.ticks,
      clients_per_host: this.form.get('numberOfClients').value || 0
    };

    this.workloadSubmission.emit(workload);
  }

  reset() {
    this.curveForm = this._initCurveForm;
  }

  remove() {
    this.removeWorkload.emit()
  }
}
