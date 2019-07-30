import {Inject, Injectable} from '@angular/core';
import {Submission} from "../models/Submission";
import {Observable, of} from "rxjs";
import {HttpClient} from "@angular/common/http";
import {Service} from "../models/Service";
import {ServiceService} from "./service.service";
import {Experiment} from "../models/Experiment";

@Injectable({
  providedIn: 'root'
})
export abstract class ExperimentService {

  abstract submit(submission: Submission): Observable<string>;

  abstract findAll(): Observable<Experiment[]>;
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

  findAll(): Observable<Experiment[]> {
    const experiments = [
      {
        id: 'asdfklj-r3jkffa',
        creator: 'Philipp',
        name: 'Important Experiment',
        start: new Date().getTime(),
        end: new Date().getTime() + 100000,
        created: new Date().getTime() - 1000,
        status: 'finished'
      },
      {
        id: 'asdfklj-rasdg3jkffa',
        status: 'queued'
      },
      {
        id: 'asdfklj-r3jkffa',
        creator: 'Philipp',
        name: 'Test Peaks',
        start: new Date().getTime(),
        created: new Date().getTime() - 10000,
        status: 'running'
      },
      {
        id: 'asdfklj-r3jkffa',
        creator: 'User1',
        name: 'low load',
        start: new Date().getTime(),
        created: new Date().getTime() - 10500,
        status: 'queued'
      },
    ];
    return of(experiments);
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

  findAll(): Observable<Experiment[]> {
    return this.httpClient.get<Experiment[]>(this.baseUrl + "/experiments");
  }


}
