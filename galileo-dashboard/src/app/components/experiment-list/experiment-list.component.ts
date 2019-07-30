import {Component, Input, OnInit} from '@angular/core';
import {Experiment} from "../../models/Experiment";

@Component({
  selector: 'app-experiment-list',
  templateUrl: './experiment-list.component.html',
  styleUrls: ['./experiment-list.component.css']
})
export class ExperimentListComponent implements OnInit {

  @Input()
  experiments: Experiment[];

  constructor() { }

  ngOnInit() {
  }

}
