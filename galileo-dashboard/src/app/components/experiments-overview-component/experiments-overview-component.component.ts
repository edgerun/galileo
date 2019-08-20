import {ChangeDetectionStrategy, Component, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {Experiment} from "../../models/Experiment";

@Component({
  selector: 'app-experiments-overview-component',
  templateUrl: './experiments-overview-component.component.html',
  styleUrls: ['./experiments-overview-component.component.css'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ExperimentsOverviewComponentComponent implements OnInit {

  private _experiments: Experiment[];

  @Input()
  loading: Map<string, boolean>;

  @Output()
  deleteExperiment: EventEmitter<string> = new EventEmitter<string>();

  @Input()
  set experiments(value: Experiment[]) {
    if (value) {
      this._experiments = value;
    } else {
      this._experiments = [];
    }
  }

  get experiments() {
    return this._experiments || [];
  }

  constructor() {
  }

  ngOnInit() {
  }

  queuedExperiments() {
    return this.experiments.filter(e => e.status.toLowerCase() === 'queued').sort((a, b) => this.sort(a, b));
  }

  private sort(a: Experiment, b: Experiment): number {
    return a.created - b.created;
  }

  finishedExperiments() {
    return this.experiments.filter(e => e.status.toLowerCase() === 'finished').sort((a, b) => a.end - b.end).reverse();
  }

  runningExperiments() {
    return this.experiments.filter(e => e.status.toLowerCase() === 'in_progress');
  }

}
