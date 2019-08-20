import {Component, EventEmitter, Inject, Input, OnInit, Output} from '@angular/core';
import {Experiment} from "../../models/Experiment";

@Component({
  selector: 'app-simple-experiment-list-item',
  templateUrl: './simple-experiment-list-item.component.html',
  styleUrls: ['./simple-experiment-list-item.component.css']
})
export class SimpleExperimentListItemComponent implements OnInit {

  @Input()
  experiment: Experiment;

  @Output()
  deleteEvent: EventEmitter<string> = new EventEmitter<string>();

  @Input()
  loading: boolean;

  constructor(@Inject('GRAFANA_URL') private grafanaUrl: string) {
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

  delete() {
    if (confirm("Are you sure to delete experiment " + this.experiment.id)) {
      this.deleteEvent.emit(this.experiment.id);
    }
  }
}
