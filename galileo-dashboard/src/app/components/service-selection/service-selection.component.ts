import {Component, Input, OnInit} from '@angular/core';
import {Service} from "../../models/Service";
import {FormGroup} from "@angular/forms";

@Component({
  selector: 'app-service-selection',
  templateUrl: './service-selection.component.html',
  styleUrls: ['./service-selection.component.css']
})
export class ServiceSelectionComponent implements OnInit {

  @Input()
  services: Service[];

  @Input()
  form: FormGroup;

  constructor() { }

  ngOnInit() {
  }

}
