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
  selectedPolicy: LoadBalancingPolicySchema;

  @Input()
  set policy(lb: LoadBalancingPolicy) {
    if (lb) {
      if (lb.config) {
        this.selectedPolicy = {
          policy: lb.policy,
          schema: {
            schema: this.policies.filter(v => v.policy == lb.policy)[0].schema.schema,
            data: lb.config
          }
        };
      } else {
        this.selectedPolicy = {
          policy: lb.policy
        };
      }
      this.form.get('selectedPolicy').setValue(this.selectedPolicy);
    }
  }


  @Input()
  policies: LoadBalancingPolicySchema[];

  @Output()
  update: EventEmitter<any> = new EventEmitter<LoadBalancingPolicy>();

  form: FormGroup;

  widgets = {
    submit: NoneComponent
  };

  constructor(private fb: FormBuilder) {

  }

  comparePolicies(one, two) {
    if (one && two) {
      return one.policy == two.policy;
    } else {
      return true;
    }
  }

  ngOnInit() {
    this.form = this.fb.group({
      'selectedPolicy': [this.selectedPolicy || undefined, []]
    });

    this.form.get('selectedPolicy').valueChanges.subscribe(v => {
      if (v && this.selectedPolicy && v.policy != this.selectedPolicy.policy) {

        let value = {policy: v.policy};
        if (v.config) {
          value['config'] = v.config;
        }
        if (v.schema) {
          this.selectedPolicy = {
            policy: v.policy,
            schema: {
              schema: v.schema.schema,
              data: v.schema.data
            }
          };
        } else {
          this.selectedPolicy = {
            policy: v.policy,
          };
        }

        this.form.get('selectedPolicy').setValue(this.selectedPolicy);
        this.update.emit(value);
      }
    })
  }

  valid(valid: boolean) {
    this.isValid = valid;
  }

  changes($event: any) {
    console.info($event);
    const v = this.form.get('selectedPolicy').value;
    this.update.emit({
      policy: v.policy,
      config: $event
    });

    this.selectedPolicy = {
      policy: v.policy,
      schema: {
        schema: v.schema.schema,
        data: $event
      }
    };
    this.form.get('selectedPolicy').setValue(this.selectedPolicy);
  }

}
