import { Component, OnInit } from '@angular/core';
import {ExperimentService} from "../../services/experiment.service";
import {Observable} from "rxjs";
import {Experiment} from "../../models/Experiment";

@Component({
  selector: 'app-experiments-overview',
  templateUrl: './experiments-overview.component.html',
  styleUrls: ['./experiments-overview.component.css']
})
export class ExperimentsOverviewComponent implements OnInit {

  experiments$: Observable<Experiment[]>;

  constructor(private experimentsService: ExperimentService) { }

  ngOnInit() {
    this.experiments$ = this.experimentsService.findAll();
  }

}
