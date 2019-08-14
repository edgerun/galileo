import {Component, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {convertToSeconds, Time, TimeUnit, timeUnits} from "../../models/TimeUnit";
import {CurveForm} from "../../models/ExperimentForm";
import {FormBuilder, FormGroup, Validators} from "@angular/forms";
import {Service} from "../../models/Service";
import * as d3 from 'd3';
import {Submission} from "../../models/Submission";
import {ExperimentConfiguration, WorkloadConfiguration} from "../../models/ExperimentConfiguration";
import * as uuid from 'uuid/v4';
import {LoadBalancingPolicy, LoadBalancingPolicySchema} from "../../models/LoadBalancingPolicy";
import {NgbModal} from '@ng-bootstrap/ng-bootstrap';

@Component({
  selector: 'app-experiment-form',
  templateUrl: './experiment-form.component.html',
  styleUrls: ['./experiment-form.component.css']
})
export class ExperimentFormComponent implements OnInit {

  @Input()
  services: Service[];

  @Input()
  lbPolicies: LoadBalancingPolicySchema[];

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
    curve: d3.curveCatmullRom
  };

  workloads: [string, WorkloadConfiguration][];
  calculatedWorkloads: Map<string, WorkloadConfiguration>;
  private lbPolicy: LoadBalancingPolicy;

  constructor(private fb: FormBuilder, private modalService: NgbModal) {
  }

  ngOnInit() {
    this.durationTime = new Time(100, timeUnits[0].id);
    this.intervalTime = new Time(10, timeUnits[0].id);
    this.workloads = [];
    this.calculatedWorkloads = new Map<string, WorkloadConfiguration>();

    this.workloads.push([uuid(), {
      clients_per_host: 3, service: "", ticks: [], arrival_pattern: ""
    }]);

    this.form = this.fb.group({
      name: ['', []],
      creator: ['', []],
      interval: [10, [Validators.required, Validators.pattern('[0-9]*')]],
      intervalUnit: [timeUnits[0], Validators.required],
      duration: [100, [Validators.required, Validators.pattern('[0-9]*')]],
      durationUnit: [timeUnits[0], Validators.required],
      maxRps: [1000, [Validators.required, Validators.pattern('[0-9]*')]],
      lbPolicy: [undefined, Validators.required]
    });

    this.form.get('duration').valueChanges.subscribe(val => {
      this.durationTime = new Time(+val, this.form.get('durationUnit').value.id);
    });

    this.form.get('durationUnit').valueChanges.subscribe(val => {
      this.durationTime = new Time(+this.form.get('duration').value, val.id);
    });

    this.form.get('interval').valueChanges.subscribe(val => {
      this.intervalTime = new Time(+val, this.form.get('intervalUnit').value.id);
    });

    this.form.get('intervalUnit').valueChanges.subscribe(val => {
      this.intervalTime = new Time(+this.form.get('interval').value, val.id);
    });
  }

  submit() {
    const configValidation: [boolean, string[]] = this.configurationsAreValid();
    if (!this.form.invalid && configValidation[0]) {
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
    } else {
      this.errorMessage = configValidation[1][0] || "Form is invalid";
      setTimeout(() => {
        this.errorMessage = '';
      }, 2000)
    }
  }

  experimentAsJson = JSON.stringify({});

  export(content) {
    const configuration = this.getConfiguration();

    let submission: Submission = {
      configuration
    };

    const experiment = this.getOptionalInput();

    submission = {
      ...submission,
      experiment
    };

    this.experimentAsJson = JSON.stringify(submission, null, 2);
    console.log(this.experimentAsJson);

    this.modalService.open(content, {ariaLabelledBy: 'modal-basic-title', size: 'lg', scrollable: true});
  }


  private configurationsAreValid(): [boolean, string[]] {
    console.log('validate configurations');
    console.log(this.calculatedWorkloads);
    if (this.calculatedWorkloads.size == 0) {
      const a: [boolean, string[]] = [false, ["No workloads defined"]];
      return a;
    }
    const errors = [...this.calculatedWorkloads.values()].map(workload => {
      const clients = workload.clients_per_host && workload.clients_per_host != 0;
      if (!clients) {
        const a: [boolean, string[]] = [false, ["Number of clients is empty/0."]];
        return a;
      }

      const service = workload.service && workload.service !== '';
      if (!service) {
        const a: [boolean, string[]] = [false, ["No service chosen."]]
        return a;
      }

      const ticks = workload.ticks.length != 0;
      if (ticks) {
        const onlyZeros = workload.ticks.every(val => val === 0);
        if (onlyZeros) {
          const a: [boolean, string []] = [false, ["Workload is empty."]];
          return a;
        }
      }

      const a: [boolean, string[]] = [true, []];
      return a;
    }).reduce((a, b) => [a[0] && b[0], a[1].concat(b[1])], [true, []]);
    return errors;
  }

  durationTime: Time;
  intervalTime: Time;
  weighted: any = {
    "round_robin": false,
    "weights": {
      "heisenberg": 2,
      "einstein": 2,
      "planck": 2,
      "testla": 2
    }
  };

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

  handleWorkloadSubmission(i: string, workload: WorkloadConfiguration) {
    console.info('handleWorkloadSubmission');
    console.info(workload);
    this.calculatedWorkloads.set(i, workload);
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
      workloads: [...this.calculatedWorkloads.values()]
    };
    return configuration;
  }

  removeWorkload(key: string) {
    this.workloads = this.workloads.filter(val => val[0] !== key);
    this.calculatedWorkloads.delete(key);
  }

  addWorkload() {
    const id = uuid();
    console.log(id);
    this.workloads.push([id, {
      clients_per_host: 3, service: "", ticks: [], arrival_pattern: ""
    }]);

  }


  handlePolicyUpdate(policy: LoadBalancingPolicy) {
    console.info(policy);
    this.lbPolicy = policy;
    this.form.get('lbPolicy').setValue(policy);
  }
}
