import {Injectable} from '@angular/core';
import {Observable, of} from "rxjs";
import {Service} from "../models/Service";

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
      id: 'asdf',
      name: 'MXNet'
    },
    {
      id: 'bdgjk',
      name: 'AlexNet'
    }
  ];

  constructor() {
  }

  findAll(): Observable<Service[]> {
    return of(this.services);
  }
}
