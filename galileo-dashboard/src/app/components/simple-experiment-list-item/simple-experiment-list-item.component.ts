import {Component, Inject, Input, OnInit} from '@angular/core';
import {Experiment} from "../../models/Experiment";
import {ExperimentService} from "../../services/experiment.service";

@Component({
  selector: 'app-simple-experiment-list-item',
  templateUrl: './simple-experiment-list-item.component.html',
  styleUrls: ['./simple-experiment-list-item.component.css']
})
export class SimpleExperimentListItemComponent implements OnInit {

  @Input()
  experiment: Experiment;

  constructor(@Inject('GRAFANA_URL') private grafanaUrl: string, private experimentService: ExperimentService) {
  }

  ngOnInit() {
  }

  getGrafanaLink(): string {
    let start;
    let end;
    if (this.experiment.status.toLowerCase() === 'finished') {
      start = this.prepareTimeForGrafana(this.experiment.start);
      end = this.prepareTimeForGrafana(this.experiment.end);
    } else {
      start = this.prepareTimeForGrafana(this.experiment.start);
      end = 'now&refresh=5s';
    }
    return `http://${this.grafanaUrl}/d/wbwBiuNZk/sandbox?orgId=1&from=${start}&to=${end}`;

  }

  private prepareTimeForGrafana(time: number): number {
    return Math.ceil(time * 1000);
  }

  delete(experiment: Experiment) {
    if (confirm("Are you sure to delete experiment " + experiment.id)) {
      console.info('deleting', experiment.id);
      // TODO: use event emitter to also remove from list
      this.experimentService.delete(experiment).subscribe(succ => {
        console.info(succ);
      }, err => {
        console.info('failed', err);
      });
    }
  }
}
