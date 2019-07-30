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
    return this.experiments.filter(e => e.status === 'queued');
  }

  finishedExperiments() {
    return this.experiments.filter(e => e.status === 'finished');
  }

  runningExperiments() {
    return this.experiments.filter(e => e.status === 'running');
  }
}
