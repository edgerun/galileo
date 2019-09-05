import {Injectable} from '@angular/core';
import {HttpEvent, HttpHandler, HttpInterceptor, HttpRequest} from '@angular/common/http';
import {Observable, throwError} from 'rxjs';
import {catchError, timeout} from 'rxjs/operators';

@Injectable()
export class TimeoutInterceptor implements HttpInterceptor {
  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    return next.handle(req).pipe(
      timeout(6000),
      catchError(e => {
          let error;
          if (e.statusText === undefined) {
            error = new Error('Timeout requesting resource');
          } else {
            error = new Error(`Error fetching experiments: ${e.statusText}`);
          }
          return throwError(error);
        }
      )
    );
  }
}
