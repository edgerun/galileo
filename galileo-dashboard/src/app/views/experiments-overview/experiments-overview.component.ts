import {Component, OnDestroy, OnInit} from '@angular/core';
import {ExperimentService} from "../../services/experiment.service";
import {Observable} from "rxjs";
import {Experiment} from "../../models/Experiment";

@Component({
  selector: 'app-experiments-overview',
  templateUrl: './experiments-overview.component.html',
  styleUrls: ['./experiments-overview.component.css']
})
export class ExperimentsOverviewComponent implements OnInit, OnDestroy {

  private interval;
  collectionSize: number;
  page: number;

  experiments$: Observable<Experiment[]>;
  experiments: Experiment[] = [];
  loading: boolean;

  constructor(private experimentsService: ExperimentService) {
  }

  ngOnInit() {
    this.findAll();
    this.interval = setInterval(() => {
      this.findAll();
    }, 5000);
  }

  ngOnDestroy(): void {
    if (this.interval && this.interval != -1) {
      clearInterval(this.interval);
      this.interval = -1;
    }
  }

  refresh() {
    this.findAll();
  }

  private findAll() {
    this.loading = true;
    this.experiments$ = this.experimentsService.findAll();
    this.experiments$.subscribe(data => {
      this.loading = false;
      this.experiments = data;
      this.collectionSize = data.length;
    })
  }
}
