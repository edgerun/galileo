import {Inject, Injectable} from '@angular/core';
import {Submission} from "../models/Submission";
import {Observable, of} from "rxjs";
import {HttpClient} from "@angular/common/http";
import {Service} from "../models/Service";
import {ServiceService} from "./service.service";

@Injectable({
  providedIn: 'root'
})
export abstract class ExperimentService {

  abstract submit(submission: Submission): Observable<string>;
}


@Injectable(
  {
    providedIn: 'root'
  }
)
export class MockExperimentService implements ExperimentService {
  submit(submission: Submission): Observable<string> {
    console.info('submitted');
    console.info(submission);
    return of('fakeid');
  }

}

@Injectable(
  {
    providedIn: 'root'
  }
)
export class HttpExperimentService implements ExperimentService {

  constructor(
    @Inject('BASE_API_URL') private baseUrl: string,
    private httpClient: HttpClient) {
  }

  submit(submission: Submission): Observable<string> {
    return this.httpClient.post<string>(this.baseUrl + "/experiments", submission);
  }


}
