import {Component, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {convertToSeconds, TimeUnit, timeUnits} from "../../models/TimeUnit";
import {CurveForm} from "../../models/ExperimentForm";
import {FormBuilder, FormGroup, Validators} from "@angular/forms";
import {noWhitespaceValidator} from "../../utils/validators";
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

  @Output()
  add = new EventEmitter<Submission>();

  form: FormGroup;
  curveForm: CurveForm;

  constructor(private fb: FormBuilder) {
  }

  ngOnInit() {
    this.form = this.fb.group({
      name: ['', []],
      creator: ['', []],
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
      curve: d3.curveBasis,
      ticks: []
    };

  }

  submit() {
    if (!this.form.errors) {
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

  private getConfiguration() {
    const durationValue: number = this.form.get('duration').value;
    const durationUnit: TimeUnit = this.form.get('durationUnit').value;
    const intervalValue: number = this.form.get('interval').value;
    const intervalUnit: TimeUnit = this.form.get('intervalUnit').value;
    const durationInSeconds: number = convertToSeconds(durationValue, durationUnit);
    const intervalInSeconds: number = convertToSeconds(intervalValue, intervalUnit);
    const workload: WorkloadConfiguration = {
      service: this.form.get('service').value.name,
      ticks: this.curveForm.ticks,
      clients_per_host: this.form.get('numberOfClients').value
    };

    const configuration: ExperimentConfiguration = {
      duration: `${durationInSeconds}s`,
      interval: `${intervalInSeconds}s`,
      workloads: [workload]
    };
    return configuration;
  }

  handleCurveForm(form: CurveForm) {
    this.curveForm = form;
  }
}
