import {Component, EventEmitter, Inject, Input, OnInit, Output} from '@angular/core';
import {convertSecondsToTime, convertToSeconds, Time, TimeUnitKind} from '../../models/TimeUnit';
import {CurveForm, CurveKind, ExperimentForm, Point} from '../../models/ExperimentForm';
import {FormBuilder, FormGroup, Validators} from '@angular/forms';
import {ClientApp} from '../../models/ClientApp';
import {Service} from '../../models/Service';
import {Submission} from '../../models/Submission';
import {ExperimentConfiguration, WorkloadConfiguration} from '../../models/ExperimentConfiguration';
import * as uuid from 'uuid/v4';
import {LoadBalancingPolicy, LoadBalancingPolicySchema} from '../../models/LoadBalancingPolicy';
import {NgbModal} from '@ng-bootstrap/ng-bootstrap';
import {DOCUMENT} from '@angular/common';
import {calculateNumberOfTicks, calculateValues, round} from '../../utils/calculator';
import {NGXLogger} from 'ngx-logger';

@Component({
  selector: 'app-experiment-form',
  templateUrl: './experiment-form.component.html',
  styleUrls: ['./experiment-form.component.css']
})
export class ExperimentFormComponent implements OnInit {

  constructor(private fb: FormBuilder, private modalService: NgbModal, @Inject(DOCUMENT) private document,
              private logger: NGXLogger) {
  }

  get hasWorkloadChanged(): boolean {
    for (const v of this.recalculate.values()) {
      if (v) {
        return true;
      }
    }
    return false;
  }

  get duration(): Time {
    const durationValue: number = this.form.get('duration').value;
    const durationUnit: TimeUnitKind = this.form.get('durationUnit').value;
    return new Time(durationValue, durationUnit);
  }

  get interval(): Time {
    const intervalValue: number = this.form.get('interval').value;
    const intervalUnit: TimeUnitKind = this.form.get('intervalUnit').value;
    return new Time(intervalValue, intervalUnit);
  }

  @Input()
  clientApps: ClientApp[];

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

  workloads: [string, WorkloadConfiguration][];
  calculatedWorkloads: Map<string, WorkloadConfiguration>;
  calculating = false;
  private lbPolicy: LoadBalancingPolicy;
  recalculate: Map<string, boolean>;
  durationTime: Time;
  intervalTime: Time;

  experimentAsJson = JSON.stringify({});

  ngOnInit() {
    this.recalculate = new Map();
    const duration = new Time(100, TimeUnitKind.Second);
    const interval = new Time(10, TimeUnitKind.Second);

    const uuid1 = uuid();
    const workloads: Map<string, WorkloadConfiguration> = new Map();
    workloads.set(uuid1, {
      clients_per_host: 3,
      service: undefined,
      ticks: [],
      arrival_pattern: 'Constant',
      maxRps: 1000,
      curve: this.initCurveForm(100),
      client: ''
    });

    const expForm: ExperimentForm = {
      experiment: {},
      workloads,
      duration,
      interval,
    };

    this.initForm(expForm);
  }

  private initForm(expForm: ExperimentForm) {
    this.durationTime = expForm.duration;
    this.intervalTime = expForm.interval;
    this.workloads = [...expForm.workloads.entries()];
    this.calculatedWorkloads = expForm.workloads;

    this.form = this.fb.group({
      name: [expForm.experiment.creator || '', []],
      creator: [expForm.experiment.name || '', []],
      interval: [expForm.interval.value, [Validators.required, Validators.pattern('[0-9]*')]],
      intervalUnit: [expForm.interval.kind, Validators.required],
      duration: [expForm.duration.value, [Validators.required, Validators.pattern('[0-9]*')]],
      durationUnit: [expForm.duration.kind, Validators.required],
      lbPolicy: [expForm.policy || undefined]
    });
    [...expForm.workloads.keys()].forEach(id => this.recalculate.set(id, true));


    this.form.get('duration').valueChanges.subscribe(val => {
      this.durationTime = new Time(+val, this.form.get('durationUnit').value);
    });

    this.form.get('durationUnit').valueChanges.subscribe(val => {
      this.durationTime = new Time(+this.form.get('duration').value, val);
    });

    this.form.get('interval').valueChanges.subscribe(val => {
      this.intervalTime = new Time(+val, this.form.get('intervalUnit').value);
    });

    this.form.get('intervalUnit').valueChanges.subscribe(val => {
      this.intervalTime = new Time(+this.form.get('interval').value, val);
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
    } else {
      this.calculating = false;
      this.errorMessage = configValidation[1][0] || 'Form is invalid';
      setTimeout(() => {
        this.errorMessage = '';
      }, 2000);
    }
  }

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
      const duration = +submission.configuration.duration.replace('s', '');
      submission.configuration.workloads = this.normalizePointsOfWorkloads(duration, this.calculatedWorkloads);
      this.calculating = false;

      this.experimentAsJson = JSON.stringify(submission, null, 2);

      this.modalService.open(content, {ariaLabelledBy: 'modal-basic-title', size: 'lg', scrollable: true});
    });

  }

  private normalizePointsOfWorkloads(duration: number, workloads: Map<string, WorkloadConfiguration>): WorkloadConfiguration[] {
    return [...workloads.entries()].map(([id, workload]) => {
      const width = workload.curve.points[workload.curve.points.length - 1].x;
      const height = workload.curve.points[0].y;

      const maxX = duration;
      const maxY = workload.maxRps;

      function map(val: number, A: number, B: number, a: number, b: number): number {
        return round((val - A) * ((b - a) / (B - A)) + a, 5);
      }

      const copiedWorkload = {
        service: workload.service,
        client: workload.client,
        ticks: workload.ticks,
        clients_per_host: workload.clients_per_host,
        arrival_pattern: workload.arrival_pattern,
        maxRps: workload.maxRps,
        curve: {
          interpolation: workload.curve.interpolation,
          points: workload.curve.points.map(p => p)
        }
      };
      copiedWorkload.curve.points = workload.curve.points.map(point => {
        return {
          x: map(map(point.x, 0, width, 0, maxX), 0, maxX, 0, 100),
          y: map(map(point.y, 0, height, maxY, 0), maxY, 0, 100, 0)
        };
      });

      return copiedWorkload;
    });

  }

  private configurationsAreValid(): [boolean, string[]] {
    if (this.calculatedWorkloads.size === 0) {
      return [false, ['No workloads defined']] as [boolean, string[]];
    }

    return [...this.calculatedWorkloads.values()].map(workload => {
      const clients = workload.clients_per_host && workload.clients_per_host !== 0;
      if (!clients) {
        return [false, ['Number of clients is empty/0.']] as [boolean, string[]];
      }

      const service = workload.service && workload.service !== '';
      if (!service) {
        return [false, ['No service chosen.']] as [boolean, string[]];
      }

      const clientApp = workload.client && workload.client !== '';
      if (!clientApp) {
        return [false, ['No clientApp chosen.']] as [boolean, string[]];
      }

      const ticks = workload.ticks.length !== 0;
      if (ticks) {
        const onlyZeros = workload.ticks.every(val => val === 0);
        if (onlyZeros) {
          return [false, ['Workload is empty.']] as [boolean, string[]];
        }
      }

      return [true, []] as [boolean, string[]];
    }).reduce((a, b) => [a[0] && b[0], a[1].concat(b[1])], [true, []]);
  }


  private initCurveForm(maxX: number): CurveForm {
    return {
      points: [{x: 0, y: 0}, {x: maxX, y: 0}],
      interpolation: CurveKind.CatMull,
      ticks: []
    };
  }

  private getOptionalInput() {
    let experiment: { name?: string, creator?: string } = {};

    if (this.form.get('name').value.length > 0) {
      experiment = {
        ...experiment,
        name: this.form.get('name').value
      };
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
    this.logger.debug(`handleWorkloadSubmission: ${workload}`);
    this.recalculate.set(i, true);
    const updated = {
      ...workload,
      ticks: this.calculatedWorkloads.get(i).ticks
    };
    this.calculatedWorkloads.set(i, updated);
  }

  private getConfiguration() {
    const durationValue: number = this.form.get('duration').value;
    const durationUnit: TimeUnitKind = this.form.get('durationUnit').value;
    const intervalValue: number = this.form.get('interval').value;
    const intervalUnit: TimeUnitKind = this.form.get('intervalUnit').value;
    const durationInSeconds: number = convertToSeconds(durationValue, durationUnit);
    const intervalInSeconds: number = convertToSeconds(intervalValue, intervalUnit);


    const configuration: ExperimentConfiguration = {
      duration: `${durationInSeconds}s`,
      interval: `${intervalInSeconds}s`,
      workloads: [...this.calculatedWorkloads.values()],
      policy: this.lbPolicy
    };
    return configuration;
  }

  removeWorkload(key: string) {
    this.workloads = this.workloads.filter(val => val[0] !== key);
    this.calculatedWorkloads.delete(key);
  }

  addWorkload() {
    const id = uuid();
    const workload = {
      clients_per_host: 3,
      service: '',
      ticks: [],
      arrival_pattern: 'Constant',
      maxRps: 1000,
      curve: this.initCurveForm(100),
      client: ''
    };
    this.workloads.push([id, workload]);

    this.calculatedWorkloads.set(id, workload);

  }

  private calculateWorkloads(): Promise<Map<string, WorkloadConfiguration>> {
    this.logger.debug('calculate');

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


    });
  }

  private calculateValues() {
    const instance = this;
    const a = new Map([...this.calculatedWorkloads.entries()].map((t: [string, WorkloadConfiguration]) => {
      const id: string = t[0];
      const workload: WorkloadConfiguration = t[1];
      if (this.recalculate.get(id)) {
        const points = workload.curve.points;
        const duration: Time = instance.duration;
        const interval: Time = instance.interval;
        const maxRps = workload.maxRps;
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

  copyToClipboard(experimentAsJson: string) {
    navigator.clipboard.writeText(experimentAsJson).finally();
  }

  handlePolicyUpdate(policy: LoadBalancingPolicy) {
    this.lbPolicy = policy;
  }

  openImportModal(modal) {
    this.modalService.open(modal, {
      ariaLabelledBy: 'import-modal-basic-title',
      size: 'lg',
      scrollable: true,
    });
  }

  import(config: string) {
    try {
      const submission: Submission = JSON.parse(config);
      const workloads: Map<string, WorkloadConfiguration> = new Map();
      for (const workload of submission.configuration.workloads) {
        workload.curve.ticks = [];
        workloads.set(uuid(), workload);
      }
      const expConfig: ExperimentForm = {
        interval: convertSecondsToTime(submission.configuration.interval),
        duration: convertSecondsToTime(submission.configuration.duration),
        workloads,
        experiment: submission.experiment,
        policy: submission.configuration.policy,
      };
      this.initForm(expConfig);
    } catch (e) {
      // TODO show error message to user
    }

  }


}

