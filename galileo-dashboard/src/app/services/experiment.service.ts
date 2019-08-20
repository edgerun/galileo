import {Inject, Injectable} from '@angular/core';
import {Submission} from "../models/Submission";
import {Observable, of} from "rxjs";
import {HttpClient} from "@angular/common/http";
import {Experiment} from "../models/Experiment";

@Injectable({
  providedIn: 'root'
})
export abstract class ExperimentService {

  abstract submit(submission: Submission): Observable<string>;

  abstract delete(id: string): Observable<string>;

  abstract findAll(): Observable<Experiment[]>;

}

@Injectable(
  {
    providedIn: 'root'
  }
)
export class MockExperimentService implements ExperimentService {

  experiments: Experiment[];

  constructor() {
    const finishedExperiments = [];
    for (let i = 0; i < 3; i++) {
      finishedExperiments.push(
        {
          id: `${i}`,
          creator: 'Philipp',
          name: 'Important Experiment',
          start: new Date().getTime(),
          end: new Date().getTime() + 100000,
          created: new Date().getTime() - 1000000000,
          status: 'finished'
        }
      );
    }

    this.experiments = [
      ...finishedExperiments,
      {
        id: '1asdf',
        creator: 'Philipp',
        name: 'Important Experiment',
        start: new Date().getTime(),
        end: new Date().getTime() + 100000,
        created: new Date().getTime() - 1000000000,
        status: 'finished'
      },
      {
        id: '2ad',
        status: 'queued',
        created: new Date().getTime() - 100000
      },
      {
        id: '3adfb',
        creator: 'Philipp',
        name: 'Test Peaks',
        start: new Date().getTime(),
        created: new Date().getTime() - 20000000,
        status: 'running'
      },
      {
        id: '4adfbf',
        creator: 'User1',
        name: 'low load',
        start: new Date().getTime(),
        created: new Date().getTime() - 10500,
        status: 'queued'
      },
    ];
  }


  submit(submission: Submission): Observable<string> {
    console.info('submitted');
    console.info(submission);
    return of('fakeid');
  }

  delete(id: string): Observable<string> {
    console.info('deleting', id);
    this.experiments = this.experiments.filter(e => e.id !== id);
    return of(id);
  }

  findAll(): Observable<Experiment[]> {
    return of(this.experiments);
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

  delete(id: string): Observable<string> {
    const url = this.baseUrl + "/experiments/" + id;
    console.log('calling delete on ', url);
    return this.httpClient.delete<string>(url);
  }

  findAll(): Observable<Experiment[]> {
    return this.httpClient.get<Experiment[]>(this.baseUrl + "/experiments");
  }


}
