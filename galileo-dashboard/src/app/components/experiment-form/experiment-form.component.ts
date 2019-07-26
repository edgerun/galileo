import {Component, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {convertToSeconds, TimeUnit, timeUnits} from "../../models/TimeUnit";
import {CurveForm, CurveKind} from "../../models/ExperimentForm";
import {FormBuilder, FormGroup, Validators} from "@angular/forms";
import {Service} from "../../models/Service";
import * as d3 from 'd3';
import {Submission} from "../../models/Submission";
import {ExperimentConfiguration, WorkloadConfiguration} from "../../models/ExperimentConfiguration";

@Component({
  selector: 'app-experiment-form',
  templateUrl: './experiment-form.component.html',
  styleUrls: ['./experiment-form.component.css']
})
export class ExperimentFormComponent implements OnInit {

  @Input()
  services: Service[];

  @Input()
  successMessage: string;

  @Input()
  errorMessage: string;

  @Output()
  add = new EventEmitter<Submission>();

  form: FormGroup;
  curveForm: CurveForm = {
    ticks: [],
    points: [{x: 0, y: 0}, {x: 100, y: 0}],
    curve: d3.curveBasis
  };
  workloads: Map<number, WorkloadConfiguration>;

  constructor(private fb: FormBuilder) {
    this.curveForm
  }

  ngOnInit() {
    this.form = this.fb.group({
      name: ['', []],
      creator: ['', []],
      interval: [10, [Validators.required, Validators.pattern('[0-9]*')]],
      intervalUnit: [timeUnits[0], Validators.required],
      duration: [100, [Validators.required, Validators.pattern('[0-9]*')]],
      durationUnit: [timeUnits[0], Validators.required],
      maxRps: [1000, [Validators.required, Validators.pattern('[0-9]*')]],
    });


  }


  submit() {
    if (!this.form.invalid) {
      const configuration = this.getConfiguration();

      let submission: Submission = {
        configuration
      };

      const experiment = this.getOptionalInput();

      submission = {
        ...submission,
        experiment
      };

      this.add.emit(submission);
    }


  }


  private initCurveForm() {
    return {
      points: [{x: 0, y: 0}, {x: this.form.get('duration').value, y: 0}],
      curve: d3.curveBasis,
      ticks: []
    };
  }

  private getOptionalInput() {
    let experiment: { name?: string, creator?: string } = {};

    if (this.form.get('name').value.length > 0) {
      experiment = {
        ...experiment,
        name: this.form.get('name').value
      }
    }

    if (this.form.get('creator').value.length > 0) {
      experiment = {
        ...experiment,
        creator: this.form.get('creator').value
      };
    }

    return experiment;
  }

  handleWorkloadSubmission(i: number, workload: WorkloadConfiguration) {
    this.workloads.set(i, workload);
  }

  private getConfiguration() {
    const durationValue: number = this.form.get('duration').value;
    const durationUnit: TimeUnit = this.form.get('durationUnit').value;
    const intervalValue: number = this.form.get('interval').value;
    const intervalUnit: TimeUnit = this.form.get('intervalUnit').value;
    const durationInSeconds: number = convertToSeconds(durationValue, durationUnit);
    const intervalInSeconds: number = convertToSeconds(intervalValue, intervalUnit);


    const configuration: ExperimentConfiguration = {
      duration: `${durationInSeconds}s`,
      interval: `${intervalInSeconds}s`,
      workloads: [...this.workloads.values()]
    };
    return configuration;
  }
}
