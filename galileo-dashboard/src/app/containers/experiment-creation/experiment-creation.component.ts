import {Component, OnInit} from '@angular/core';
import {ServiceService} from "../../services/service.service";
import {Observable} from "rxjs";
import {Service} from "../../models/Service";
import {ExperimentForm} from "../../models/ExperimentForm";
@Component({
  selector: 'app-experiment-creation',
  templateUrl: './experiment-creation.component.html',
  styleUrls: ['./experiment-creation.component.css']
})
export class ExperimentCreationComponent implements OnInit {

  services: Observable<Service[]>;

  constructor(private serviceService: ServiceService) { }




  ngOnInit() {
    console.info(this.serviceService);
    this.services = this.serviceService.findAll();
  }

  submitExperiment($event: ExperimentForm) {

  }
}
