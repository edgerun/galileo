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
  error: string;
  success: string;

  experiments$: Observable<Experiment[]>;
  experiments: Experiment[] = [];
  loadingMap: Map<string, boolean> = new Map();
  loading: boolean;
  timeout: any;

  constructor(private experimentsService: ExperimentService) {
  }

  ngOnInit() {
    this.findAll();
  }

  ngOnDestroy(): void {
    if (this.interval && this.interval != -1) {
      clearInterval(this.interval);
      this.interval = -1;
    }
  }

  refresh() {
    this.error = null;
    this.loading = false;
    this.findAll();
  }

  private findAll() {
    clearInterval(this.interval);
    this.loading = true;
    this.experiments$ = this.experimentsService.findAll();
    this.experiments$.subscribe(data => {
      this.loading = false;
      this.experiments = data;
      this.collectionSize = data.length;
      this.interval = setInterval(() => {
        this.findAll();
      }, 6500);
    }, (error: Error) => {
      this.changeErrorMessage(error.message);
      this.loading = false;
    })
  }

  private changeErrorMessage(text: string) {
    clearTimeout(this.timeout);
    this.error = text;
    this.timeout = setTimeout(() => {
      this.error = null;
    }, 3000)
  }

  private changeSuccessMessage(text: string) {
    clearTimeout(this.timeout);
    this.success = text;
    this.timeout = setTimeout(() => {
      this.success = null;
    }, 3000)
  }

  deleteExperiment(id: string) {
    this.loadingMap.set(id, true);
    this.experimentsService.delete(id).subscribe(() => {
      this.changeSuccessMessage(`Experiment ${id} got removed.`);
      this.experiments = this.experiments.filter(e => e.id !== id);
      this.loadingMap.set(id, false);
    }, (err: Error) => {
      console.error(`Error cancelling experiment ${id}. ${err}`);
      this.changeErrorMessage(`Error happened cancelling experiment ${id}. ${err.message}`);
      this.loadingMap.set(id, false);
    });
  }
}
