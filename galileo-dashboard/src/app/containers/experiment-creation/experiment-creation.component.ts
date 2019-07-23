import {Component, OnInit} from '@angular/core';
import {ServiceService} from "../../services/service.service";
import {Observable} from "rxjs";
import {Service} from "../../models/Service";
import {ExperimentForm} from "../../models/ExperimentForm";
import {ExperimentService} from "../../services/experiment.service";
import {Submission} from "../../models/Submission";
@Component({
  selector: 'app-experiment-creation',
  templateUrl: './experiment-creation.component.html',
  styleUrls: ['./experiment-creation.component.css']
})
export class ExperimentCreationComponent implements OnInit {

  services$: Observable<Service[]>;

  constructor(private serviceService: ServiceService, private experimentService: ExperimentService) { }




  ngOnInit() {
    this.services$ = this.serviceService.findAll();
  }

  submitExperiment($event: Submission) {
    this.experimentService.submit($event);
  }
}
