import {Component, Input, OnInit} from '@angular/core';
import {timeUnits} from "../../models/TimeUnit";
import {FormGroup} from "@angular/forms";

@Component({
  selector: 'app-time-input',
  templateUrl: './time-input.component.html',
  styleUrls: ['./time-input.component.css']
})
export class TimeInputComponent implements OnInit {

  readonly timeUnits = timeUnits;


  @Input()
  name: string;

  @Input()
  form: FormGroup;

  @Input()
  unitFormControl: string;

  @Input()
  timeFormControl: string;

  constructor() { }

  ngOnInit() {
    this.form.get(this.unitFormControl).valueChanges.subscribe(e => console.log(e));
  }

}
