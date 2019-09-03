import {Inject, Injectable} from '@angular/core';
import {Observable, of} from "rxjs";
import {Service} from "../models/Service";
import {HttpClient} from "@angular/common/http";
import {ClientApp} from "../models/ClientApp";

@Injectable({
  providedIn: 'root'
})
export abstract class ClientAppService {

  abstract findAll(): Observable<ClientApp[]>;
}


@Injectable(
  {
    providedIn: 'root'
  }
)
export class MockClientAppService implements ClientAppService {

  readonly items: ClientApp[] = [
    {
      name: 'mock-mms-client',
      manifest: {}
    }
  ];

  constructor() {
  }

  findAll(): Observable<ClientApp[]> {
    return of(this.items);
  }
}

@Injectable(
  {
    providedIn: 'root'
  }
)
export class HttpClientAppService implements ClientAppService {

  constructor(
    @Inject('BASE_API_URL') private baseUrl: string,
    private httpClient: HttpClient) {
  }

  findAll(): Observable<ClientApp[]> {
    return this.httpClient.get<ClientApp[]>(this.baseUrl + "/apps")
  }

}
