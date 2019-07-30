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
}
