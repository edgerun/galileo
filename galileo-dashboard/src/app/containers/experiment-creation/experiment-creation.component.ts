import {Component, OnInit} from '@angular/core';
import {ServiceService} from "../../services/service.service";
import {Observable, of, Subject} from "rxjs";
import {Service} from "../../models/Service";
import {ExperimentService} from "../../services/experiment.service";
import {Submission} from "../../models/Submission";
import {debounceTime} from "rxjs/operators";
import {LoadBalancingPolicyService} from "../../services/load-balancing-policy.service";
import {LoadBalancingPolicy, LoadBalancingPolicySchema} from "../../models/LoadBalancingPolicy";

@Component({
  selector: 'app-experiment-creation',
  templateUrl: './experiment-creation.component.html',
  styleUrls: ['./experiment-creation.component.css']
})
export class ExperimentCreationComponent implements OnInit {

  services$: Observable<Service[]>;
  lbPolicies$: Observable<LoadBalancingPolicySchema[]>;
  _success = new Subject<string>();
  _error = new Subject<string>();

  constructor(private serviceService: ServiceService, private experimentService: ExperimentService,
              private lbPolicyService: LoadBalancingPolicyService) {
  }


  ngOnInit() {
    this.services$ = this.serviceService.findAll();
    this.lbPolicies$ = this.lbPolicyService.findAll();
    this._success.pipe(
      debounceTime(3000)
    ).subscribe(() => this._success.next(null));
  }

  private changeSuccessMessage(text: string) {
    this._success.next(text)
  }

  private changeErrorMessage(text: string) {
    this._error.next(text);
  }

  submitExperiment($event: Submission) {
    this.experimentService.submit($event).subscribe(succ => {
      console.info(succ);
      this.changeSuccessMessage(`Experiment submitted. ID: ${succ}`)
    }, err => {
      this.changeErrorMessage(`Error submitting experiment: ${err.message}`)
    });
  }
}
