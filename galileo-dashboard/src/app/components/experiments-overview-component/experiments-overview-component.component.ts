import {Component, Input, OnInit} from '@angular/core';
import {Experiment} from "../../models/Experiment";

@Component({
  selector: 'app-experiments-overview-component',
  templateUrl: './experiments-overview-component.component.html',
  styleUrls: ['./experiments-overview-component.component.css']
})
export class ExperimentsOverviewComponentComponent implements OnInit {

  @Input()
  experiments: Experiment[];

  constructor() {
  }

  ngOnInit() {
  }

  queuedExperiments() {
    return this.experiments.filter(e => e.status === 'queued').sort((a,b) => -1 *this.sort(a,b));
  }

  private sort(a: Experiment, b: Experiment): number {
    return a.created - b.created;
  }

  finishedExperiments() {
    return this.experiments.filter(e => e.status === 'finished').sort((a,b) => this.sort(a,b));
  }

  runningExperiments() {
    return this.experiments.filter(e => e.status === 'running');
  }
}