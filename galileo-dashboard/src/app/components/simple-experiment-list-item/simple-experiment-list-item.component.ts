import {Component, Input, OnInit} from '@angular/core';
import {Experiment} from "../../models/Experiment";

@Component({
  selector: 'app-simple-experiment-list-item',
  templateUrl: './simple-experiment-list-item.component.html',
  styleUrls: ['./simple-experiment-list-item.component.css']
})
export class SimpleExperimentListItemComponent implements OnInit {

  @Input()
  experiment: Experiment;

  constructor() { }

  ngOnInit() {
  }

}
