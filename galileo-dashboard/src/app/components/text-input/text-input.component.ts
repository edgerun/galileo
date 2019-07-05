import {Component, Input, OnInit} from '@angular/core';
import {FormControl, FormGroup} from "@angular/forms";

@Component({
  selector: 'app-text-input',
  templateUrl: './text-input.component.html',
  styleUrls: ['./text-input.component.css']
})
export class TextInputComponent implements OnInit {

  @Input()
  form: FormGroup;

  @Input()
  controlName: string;

  @Input()
  name: string;

  @Input()
  placeholder: string;

  constructor() { }

  ngOnInit() {
  }

}
