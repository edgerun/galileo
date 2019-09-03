import {Component, OnInit} from '@angular/core';
import {ServiceService} from "../../services/service.service";
import {Observable, Subject} from "rxjs";
import {Service} from "../../models/Service";
import {ClientApp} from "../../models/ClientApp";
import {ExperimentService} from "../../services/experiment.service";
import {Submission} from "../../models/Submission";
import {debounceTime} from "rxjs/operators";
import {LoadBalancingPolicyService} from "../../services/load-balancing-policy.service";
import {LoadBalancingPolicy, LoadBalancingPolicySchema} from "../../models/LoadBalancingPolicy";
import {ClientAppService} from "../../services/client-app.service";

@Component({
  selector: 'app-experiment-creation',
  templateUrl: './experiment-creation.component.html',
  styleUrls: ['./experiment-creation.component.css']
})
export class ExperimentCreationComponent implements OnInit {

  services$: Observable<Service[]>;
  clientApps$: Observable<ClientApp[]>;
  lbPolicies$: Observable<LoadBalancingPolicySchema[]>;
  _success = new Subject<string>();
  _error = new Subject<string>();
  loading: boolean = false;

  constructor(private serviceService: ServiceService, private clientAppService: ClientAppService,
              private experimentService: ExperimentService, private lbPolicyService: LoadBalancingPolicyService) {
  }


  ngOnInit() {
    this.services$ = this.serviceService.findAll();
    this.clientApps$ = this.clientAppService.findAll();
    this.lbPolicies$ = this.lbPolicyService.findAll();
    this._success.pipe(
      debounceTime(3000)
    ).subscribe(() => this._success.next(null));

    this._error.pipe(
      debounceTime(2000)
    ).subscribe(() => this._error.next(null));
  }

  private changeSuccessMessage(text: string) {
    this._success.next(text)
  }

  private changeErrorMessage(text: string) {
    this._error.next(text);
  }

  submitExperiment($event: Submission) {
    this.loading = true;
    this.experimentService.submit($event).subscribe(succ => {
      console.info(succ);
      this.loading = false;
      this.changeSuccessMessage(`Experiment submitted. ID: ${succ}`)
    }, err => {
      this.loading = false;
      this.changeErrorMessage(`Error submitting experiment: ${err.message}`)
    });
  }
}
