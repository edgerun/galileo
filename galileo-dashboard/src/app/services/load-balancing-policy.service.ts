import {Inject, Injectable} from '@angular/core';
import {Observable, of} from "rxjs";
import {LoadBalancingPolicySchema} from "../models/LoadBalancingPolicy";
import {HttpClient} from "@angular/common/http";
import {map} from "rxjs/operators";

@Injectable({
  providedIn: 'root'
})
export abstract class LoadBalancingPolicyService {
  abstract findAll(): Observable<LoadBalancingPolicySchema[]>;
}

@Injectable({
  providedIn: 'root'
})
export class HttpLoadBalancingPolicyService implements LoadBalancingPolicyService {

  constructor(
    @Inject('SYMMETRY_API_URL') private baseUrl: string,
    private httpClient: HttpClient) {
  }

  findAll(): Observable<LoadBalancingPolicySchema[]> {
    return this.httpClient.get<LoadBalancingPolicySchema[]>(this.baseUrl + "/policies/balancing")
      .pipe(
        map((e: LoadBalancingPolicySchema[]) => {
          e.map(
            t => {
              t.schema = {
                'schema': t.schema
              };
            }
          );

          return e;
        })
      );
  }
}

@Injectable(
  {
    providedIn: 'root'
  }
)
export class MockLoadBalancingPolicyService implements LoadBalancingPolicyService {

  readonly policies: LoadBalancingPolicySchema[] = [
    {
      policy: "Weighted",
      schema: weighted
    },
    {
      policy: "Round Robin"
    },
    {
      policy: "Random"
    },
    {
      policy: "Pseudo",
      schema: pseudo
    }
  ];

  findAll(): Observable<LoadBalancingPolicySchema[]> {
    console.info(this.policies);
    return of(this.policies);
  }

}


const weighted = {
  "schema": {
    "type": "object",
    "properties": {
      "round_robin": {
        "type": "boolean"
      },
      "weights": {
        "type": "object",
        "properties": {
          "heisenberg": {
            "type": "number"
          },
          "einstein": {
            "type": "number"
          },
          "planck": {
            "type": "number"
          },
          "tesla": {
            "type": "number",
          },
        },
        "required": ["heisenberg", "tesla", "planck", "einstein"],
      },
    }
  },
  "data": {
    "round_robin": true,
    "weights": {
      "einstein": 2,
      "tesla": 2,
      "planck": 2,
      "heisenberg": 2,
    }
  }
};

const pseudo = {
  "schema:": {
    "type": "object",
    "properties": {
      "nodes": {
        "type": "object",
        "properties": {
          "heisenberg": {
            "type": "boolean"
          },
          "einstein": {
            "type": "boolean"
          },
          "planck": {
            "type": "boolean"
          },
          "tesla": {
            "type": "boolean"
          }
        }
      }
    }
  },
  "data": {
    "heisenberg": false,
    "planck": false,
    "tesla": true,
    "einstein": false
  }
};
