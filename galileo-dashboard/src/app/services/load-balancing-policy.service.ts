import {Injectable} from '@angular/core';
import {Observable, of} from "rxjs";
import {LoadBalancingPolicy} from "../models/LoadBalancingPolicy";
import * as weighted  from './mock/weighted.json';
import * as test from './mock/test.json';
@Injectable({
  providedIn: 'root'
})
export abstract class LoadBalancingPolicyService {
  abstract findAll(): Observable<LoadBalancingPolicy[]>;
}

@Injectable(
  {
    providedIn: 'root'
  }
)
export class MockLoadBalancingPolicyService implements LoadBalancingPolicyService {

  readonly policies: LoadBalancingPolicy[] = [
    {
      "name": "Weighted",
      "schema": weighted
    }
  ];

  findAll(): Observable<LoadBalancingPolicy[]> {
    console.info(this.policies);
    return of(this.policies);
  }

}


