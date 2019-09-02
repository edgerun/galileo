import {Component, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {FormBuilder, FormGroup, Validators} from "@angular/forms";
import {CurveForm, Point} from "../../models/ExperimentForm";
import {Time} from "../../models/TimeUnit";
import {WorkloadConfiguration} from "../../models/ExperimentConfiguration";
import {Service} from "../../models/Service";
import {ClientApp} from "../../models/ClientApp";

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

  @Output()
  pointsEmitted: EventEmitter<Point[]> = new EventEmitter<Point[]>();

  @Input()
  clientApps: ClientApp[];

  errorMessage: string;

  arrivalPatterns: string[] = [
    'Constant',
    'Exponential'
  ];


  constructor(private fb: FormBuilder) {
    this.form = this.fb.group({
      maxRps: [1000, [Validators.required, Validators.pattern('[0-9]*')]],
      clientApp: [undefined, Validators.required],
      service: [undefined, Validators.required],
      numberOfClients: [3, [Validators.required, Validators.pattern('[0-9]*')]],
      arrivalPattern: ['Constant', Validators.required]
    });

    this.form.get('service').valueChanges.subscribe(val => {
      this.handleCurveForm(this.calculatedForm);
    });

    this.form.get('numberOfClients').valueChanges.subscribe(val => {
      this.handleCurveForm(this.calculatedForm);
    });

    this.form.get('arrivalPattern').valueChanges.subscribe(val => {
      this.handleCurveForm(this.calculatedForm);
    })
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

    function getClient(value: ClientApp) {
      if (value) {
        return value.name;
      } else {
        return "";
      }
    }

    function getService(value: Service) {
      if (value) {
        return value.name;
      } else {
        return "";
      }
    }

    const workload: WorkloadConfiguration = {
      client: getClient(this.form.get('clientApp').value),
      service: getService(this.form.get('service').value),
      ticks: [],
      clients_per_host: this.form.get('numberOfClients').value || 0,
      arrival_pattern: this.form.get('arrivalPattern').value || ""
    };

    this.workloadSubmission.emit(workload);
  }

  reset() {
    this.curveForm = {
      curve: this._initCurveForm.curve,
      ticks: this._initCurveForm.ticks.map(t => t),
      points: this._initCurveForm.points.map(p => p)
    }
  }

  remove() {
    this.removeWorkload.emit()
  }
}
