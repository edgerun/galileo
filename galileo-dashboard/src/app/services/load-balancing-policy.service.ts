import {Injectable} from '@angular/core';
import {Observable, of} from "rxjs";
import {LoadBalancingPolicy, LoadBalancingPolicySchema} from "../models/LoadBalancingPolicy";

@Injectable({
  providedIn: 'root'
})
export abstract class LoadBalancingPolicyService {
  abstract findAll(): Observable<LoadBalancingPolicySchema[]>;
}

@Injectable(
  {
    providedIn: 'root'
  }
)
export class MockLoadBalancingPolicyService implements LoadBalancingPolicyService {

  readonly policies: LoadBalancingPolicySchema[] = [
    {
      name: "Weighted",
      schema: weighted
    },
    {
      name: "Round Robin"
    },
    {
      name: "Random"
    },
    {
      name: "Pseudo",
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
