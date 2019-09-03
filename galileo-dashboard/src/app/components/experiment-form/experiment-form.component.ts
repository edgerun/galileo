import {Component, EventEmitter, Inject, Input, OnInit, Output} from '@angular/core';
import {convertToSeconds, Time, TimeUnit, timeUnits} from "../../models/TimeUnit";
import {CurveForm, Point} from "../../models/ExperimentForm";
import {FormBuilder, FormGroup, Validators} from "@angular/forms";
import {Service} from "../../models/Service";
import * as d3 from 'd3';
import {Submission} from "../../models/Submission";
import {ExperimentConfiguration, WorkloadConfiguration} from "../../models/ExperimentConfiguration";
import * as uuid from 'uuid/v4';
import {LoadBalancingPolicy, LoadBalancingPolicySchema} from "../../models/LoadBalancingPolicy";
import {NgbModal} from '@ng-bootstrap/ng-bootstrap';
import {DOCUMENT} from "@angular/common";
import {calculateNumberOfTicks, calculateValues} from "../../utils/calculator";

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

  @Input()
  loading: boolean;

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
  workloadPoints: Map<string, Point[]> = new Map();
  calculating: boolean = false;
  private lbPolicy: LoadBalancingPolicy;
  recalculate: Map<string, boolean>;

  constructor(private fb: FormBuilder, private modalService: NgbModal, @Inject(DOCUMENT) private document) {
  }

  ngOnInit() {
    this.recalculate = new Map();
    this.durationTime = new Time(20, timeUnits[1].id);
    this.intervalTime = new Time(2, timeUnits[0].id);
    this.workloads = [];
    this.calculatedWorkloads = new Map<string, WorkloadConfiguration>();

    let id = uuid();
    this.workloads.push([id, {
      clients_per_host: 3, service: "", ticks: [], arrival_pattern: ""
    }]);

    this.calculatedWorkloads.set(id, this.workloads[0][1]);

    this.recalculate.set(id, true);

    this.form = this.fb.group({
      name: ['', []],
      creator: ['', []],
      interval: [2, [Validators.required, Validators.pattern('[0-9]*')]],
      intervalUnit: [timeUnits[0], Validators.required],
      duration: [20, [Validators.required, Validators.pattern('[0-9]*')]],
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
    this.calculating = true;
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


      this.calculateWorkloads().then(r => {
        this.calculatedWorkloads = r;
        submission.configuration.workloads = [...this.calculatedWorkloads.values()];

        this.add.emit(submission);
        this.calculating = false;
      });
      console.info('hereeeeeeeeeee');
    } else {
      this.calculating = false;
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

    this.calculating = true;
    this.calculateWorkloads().then(r => {
      this.calculatedWorkloads = r;
      submission.configuration.workloads = [...this.calculatedWorkloads.values()];
      this.calculating = false;


      this.experimentAsJson = JSON.stringify(submission, null, 2);
      console.log(this.experimentAsJson);

      this.modalService.open(content, {ariaLabelledBy: 'modal-basic-title', size: 'lg', scrollable: true});
    });

  }


  private configurationsAreValid(): [boolean, string[]] {
    console.log('validate configurations');
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
    const updated = {
      ...workload,
      ticks: this.calculatedWorkloads.get(i).ticks
    };
    this.calculatedWorkloads.set(i, updated);
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
    const workload = {
      clients_per_host: 3, service: "", ticks: [], arrival_pattern: ""
    };
    this.workloads.push([id, workload]);

    this.calculatedWorkloads.set(id, workload);
  }


  handlePolicyUpdate(policy: LoadBalancingPolicy) {
    console.info(policy);
    this.lbPolicy = policy;
    this.form.get('lbPolicy').setValue(policy);
  }

  get hasWorkloadChanged(): boolean {
    for (let v of this.recalculate.values()) {
      if (v) return true;
    }
    return false;
  }

  private calculateWorkloads(): Promise<Map<string, WorkloadConfiguration>> {
    console.info('calculate');

    return new Promise<Map<string, WorkloadConfiguration>>((resolve, reject) => {
      if (!this.hasWorkloadChanged) {
        resolve(this.calculatedWorkloads);
        return;
      }

      if (calculateNumberOfTicks(this.duration, this.interval) < 100) {
        resolve(this.calculateValues());
      } else {
        setTimeout(() => {
          resolve(this.calculateValues());
        }, 100);
      }


    })
  }

  private calculateValues() {
    const instance = this;
    const a = new Map([...this.calculatedWorkloads.entries()].map((t: [string, WorkloadConfiguration]) => {
      const id: string = t[0];
      const workload: WorkloadConfiguration = t[1];
      if (this.recalculate.get(id)) {
        const points = instance.workloadPoints.get(id);
        const duration: Time = instance.duration;
        const interval: Time = instance.interval;
        const maxRps = instance.form.get('maxRps').value;
        const svg = instance.document.getElementById(`${id}`);
        const path = svg.querySelector(`path`);
        workload.ticks = calculateValues(duration, interval, maxRps, points, path);
        this.recalculate.set(id, false);
        return [id, workload];
      } else {
        return [id, workload];
      }
    }));

    return a;
  }

  get duration(): Time {
    const durationValue: number = this.form.get('duration').value;
    const durationUnit: TimeUnit = this.form.get('durationUnit').value;
    return new Time(durationValue, durationUnit.id);
  }

  get interval(): Time {
    const intervalValue: number = this.form.get('interval').value;
    const intervalUnit: TimeUnit = this.form.get('intervalUnit').value;
    return new Time(intervalValue, intervalUnit.id);
  }

  handlePointsUpdate(id: string, $event: Point[]) {
    this.recalculate.set(id, true);
    this.workloadPoints.set(id, $event);
  }
}
