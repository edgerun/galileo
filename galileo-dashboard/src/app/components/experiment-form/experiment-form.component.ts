import {Component, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {TimeUnit, TimeUnitKind, timeUnits} from "../../models/TimeUnit";
import {ExperimentForm} from "../../models/ExperimentForm";
import {FormBuilder, Validators} from "@angular/forms";
import {noWhitespaceValidator} from "../../utils/validators";
import {Service} from "../../models/Service";

@Component({
  selector: 'app-experiment-form',
  templateUrl: './experiment-form.component.html',
  styleUrls: ['./experiment-form.component.css']
})
export class ExperimentFormComponent implements OnInit {

  @Input()
  services: Service[];

  @Output()
  add = new EventEmitter<ExperimentForm>();

  form = this.fb.group({
    name: ['', [Validators.required, noWhitespaceValidator]],
    creator: ['', [Validators.required, noWhitespaceValidator]],
    interval:[10, Validators.required],
    intervalUnit: [timeUnits[0], Validators.required],
    duration:[100, Validators.required],
    durationUnit: [timeUnits[0], Validators.required],
    service:[undefined, Validators.required]
  });

  constructor(private fb: FormBuilder) { }

  ngOnInit() {
  }

  submit() {
    console.log(this.form.value)
  }
}
