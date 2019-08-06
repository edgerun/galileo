import {Component, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {Experiment} from "../../models/Experiment";

@Component({
  selector: 'app-paginated-experiment-list',
  templateUrl: './paginated-experiment-list.component.html',
  styleUrls: ['./paginated-experiment-list.component.css']
})
export class PaginatedExperimentListComponent implements OnInit {

  @Input()
  experiments: Experiment[];

  pageSize: number = 6;

  page: number = 1;

  constructor() {
  }

  ngOnInit() {
  }

}
