import {Component, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {Experiment} from "../../models/Experiment";

@Component({
  selector: 'app-experiment-list',
  templateUrl: './experiment-list.component.html',
  styleUrls: ['./experiment-list.component.css']
})
export class ExperimentListComponent implements OnInit {

  @Input()
  experiments: Experiment[];

  @Input()
  loading: Map<string, boolean>;

  @Output()
  deleteExperiment: EventEmitter<string> = new EventEmitter<string>();

  collapsed: string = "";


  constructor() { }

  ngOnInit() {
  }

  toggle(id: string) {
    console.log(id);
    if (this.collapsed == id) {
      this.collapsed = ""
    } else {
      this.collapsed = id;
    }
  }

  cancelExperiment(id: string) {
    if (confirm(`Are you sure to cancel experiment ${id}?`)) {
      this.deleteExperiment.emit(id);
    }
  }
}
