import {ChangeDetectionStrategy, Component, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {LoadBalancingPolicy, LoadBalancingPolicySchema} from "../../models/LoadBalancingPolicy";
import {FormBuilder, FormGroup} from "@angular/forms";
import {NoneComponent} from "angular6-json-schema-form";

@Component({
  selector: 'app-load-balancing-policy-form',
  templateUrl: './load-balancing-policy-form.component.html',
  styleUrls: ['./load-balancing-policy-form.component.css'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class LoadBalancingPolicyFormComponent implements OnInit {

  private isValid: boolean;

  @Input()
  policies: LoadBalancingPolicySchema[];

  selectedPolicy: LoadBalancingPolicySchema;

  @Output()
  update: EventEmitter<any> = new EventEmitter<LoadBalancingPolicy>();

  form: FormGroup;

  widgets = {
    submit: NoneComponent
  };

  constructor(private fb: FormBuilder) {

  }

  ngOnInit() {
    this.form = this.fb.group({
      'selectedPolicy': [undefined, []]
    });

    this.form.get('selectedPolicy').valueChanges.subscribe(v => {
      if (v) {

        let value = {name: v.name};
        if (v.config)  {
          value['config'] = v.config;
        }
        this.update.emit(value);
      }
    })
  }

  valid(valid: boolean) {
    this.isValid = valid;
  }


  changes($event: any) {
    const v = this.form.get('selectedPolicy').value;
    this.update.emit({
      name: v.name,
      config: $event
    });
  }

}
