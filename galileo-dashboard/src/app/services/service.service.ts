import {Inject, Injectable} from '@angular/core';
import {Observable, of} from 'rxjs';
import {Service} from '../models/Service';
import {HttpClient} from '@angular/common/http';

@Injectable({
  providedIn: 'root'
})
export abstract class ServiceService {

  abstract findAll(): Observable<Service[]>;
}


@Injectable(
  {
    providedIn: 'root'
  }
)
export class MockServiceService implements ServiceService {

  readonly services: Service[] = [
    {
      id: 'id1',
      name: 'MXNet',
    },
    {
      id: 'id2',
      name: 'AlexNet',
    }
  ];

  constructor() {
  }

  findAll(): Observable<Service[]> {
    return of(this.services);
  }
}

@Injectable(
  {
    providedIn: 'root'
  }
)
export class HttpServiceService implements ServiceService {

  constructor(
    @Inject('SYMMETRY_API_URL') private baseUrl: string,
    private httpClient: HttpClient) {
  }

  findAll(): Observable<Service[]> {
    return this.httpClient.get<Service[]>(this.baseUrl + '/services');
  }

}
