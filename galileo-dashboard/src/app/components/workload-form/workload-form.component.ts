import {Component, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {FormBuilder, FormGroup, Validators} from '@angular/forms';
import {CurveForm, Point} from '../../models/ExperimentForm';
import {convertToSeconds, Time} from '../../models/TimeUnit';
import * as d3 from 'd3';
import {ExperimentConfiguration, WorkloadConfiguration} from '../../models/ExperimentConfiguration';
import {Service} from '../../models/Service';
import {ClientApp} from '../../models/ClientApp';

@Component({
  selector: 'app-workload-form',
  templateUrl: './workload-form.component.html',
  styleUrls: ['./workload-form.component.css']
})
export class WorkloadFormComponent implements OnInit {


  private _initCurveForm: CurveForm;
  curveForm: CurveForm;
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
  services: Service[];

  @Input()
  initWorkload: WorkloadConfiguration;

  @Input()
  clientApps: ClientApp[];

  arrivalPatterns: string[] = [
    'Constant',
    'Exponential'
  ];


  constructor(private fb: FormBuilder) {
  }

  ngOnInit(): void {
    this.form = this.fb.group({
      maxRps: [this.initWorkload.maxRps, [Validators.required, Validators.pattern('[0-9]*')]],
      service: [this.initWorkload.service || '', Validators.required],
      numberOfClients: [this.initWorkload.clients_per_host, [Validators.required, Validators.pattern('[0-9]*')]],
      arrivalPattern: [this.initWorkload.arrival_pattern, Validators.required],
      clientApp: [this.initWorkload.client || '', Validators.required]
    });

    this.form.get('service').valueChanges.subscribe(val => {
      this.handleCurveForm(this.calculatedForm);
    });

    this.form.get('numberOfClients').valueChanges.subscribe(val => {
      this.handleCurveForm(this.calculatedForm);
    });

    this.form.get('arrivalPattern').valueChanges.subscribe(val => {
      this.handleCurveForm(this.calculatedForm);
    });

    this.form.get('clientApp').valueChanges.subscribe(val => {
      this.handleCurveForm(this.calculatedForm);
    });


    this.curveForm = this.initWorkload.curve;

    this._initCurveForm = {
      interpolation: this.initWorkload.curve.interpolation,
      ticks: this.initWorkload.curve.ticks.map(t => t),
      points: this.initWorkload.curve.points.map(t => t)
    };
  }

  handleCurveForm(form: CurveForm) {
    this.calculatedForm = form;

    function getClient(value: ClientApp) {
      if (value) {
        return value.name;
      } else {
        return '';
      }
    }

    function getService(value: Service) {
      if (value) {
        return value.name;
      } else {
        return '';
      }
    }

    const workload: WorkloadConfiguration = {
      client: this.form.get('clientApp').value,
      service: this.form.get('service').value,
      ticks: [],
      clients_per_host: this.form.get('numberOfClients').value || 0,
      arrival_pattern: this.form.get('arrivalPattern').value || '',
      maxRps: +this.form.get('maxRps').value,
      curve: this.calculatedForm,
    };

    this.workloadSubmission.emit(workload);
  }

  reset() {
    this.curveForm = {
      interpolation: this._initCurveForm.interpolation,
      ticks: this._initCurveForm.ticks.map(t => t),
      points: this._initCurveForm.points.map(p => p)
    };
  }

  remove() {
    this.removeWorkload.emit();
  }
}
