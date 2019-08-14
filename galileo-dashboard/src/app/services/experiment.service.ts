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

  abstract delete(experiment: Experiment): Observable<string>;

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

  delete(experiment: Experiment): Observable<string> {
    console.info('deleting', experiment.id);
    return of(experiment.id);
  }

  findAll(): Observable<Experiment[]> {
    const finishedExperiments: Experiment[] = [];

    for (let i = 0; i < 60; i++) {
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

    const experiments = [
      ...finishedExperiments,
      {
        id: '1',
        creator: 'Philipp',
        name: 'Important Experiment',
        start: new Date().getTime(),
        end: new Date().getTime() + 100000,
        created: new Date().getTime() - 1000000000,
        status: 'finished'
      },
      {
        id: '2',
        status: 'queued',
        created: new Date().getTime() - 100000
      },
      {
        id: '3',
        creator: 'Philipp',
        name: 'Test Peaks',
        start: new Date().getTime(),
        created: new Date().getTime() - 20000000,
        status: 'running'
      },
      {
        id: '4',
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

  delete(experiment: Experiment): Observable<string> {
    const url = this.baseUrl + "/experiments/" + experiment.id;
    console.log('calling delete on ', url);
    return this.httpClient.delete<string>(url);
  }

  findAll(): Observable<Experiment[]> {
    return this.httpClient.get<Experiment[]>(this.baseUrl + "/experiments");
  }


}
