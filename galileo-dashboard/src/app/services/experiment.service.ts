import { Injectable } from '@angular/core';
import {Submission} from "../models/Submission";
import {Observable, of} from "rxjs";

@Injectable({
  providedIn: 'root'
})
export abstract class ExperimentService {

  abstract submit(submission: Submission);
}


@Injectable(
  {
    providedIn: 'root'
  }
)
export class MockExperimentService implements ExperimentService {
  submit(submission: Submission) : Observable<void> {
    console.info('submitted');
    console.info(submission);
    return of();
  }

}
