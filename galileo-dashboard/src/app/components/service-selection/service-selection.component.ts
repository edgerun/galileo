import {Component, Input, OnInit, ViewChild, ViewEncapsulation} from '@angular/core';
import {Service} from '../../models/Service';
import {FormGroup} from '@angular/forms';
import {merge, Observable, Subject} from 'rxjs';
import {debounceTime, distinctUntilChanged, filter, map} from 'rxjs/operators';
import {NgbTypeahead} from '@ng-bootstrap/ng-bootstrap';

@Component({
  selector: 'app-service-selection',
  templateUrl: './service-selection.component.html',
  styleUrls: ['./service-selection.component.css'],
  encapsulation: ViewEncapsulation.None
})
export class ServiceSelectionComponent implements OnInit {

  public model: any;

  @ViewChild('instance', {static: true}) instance: NgbTypeahead;
  focus$ = new Subject<string>();
  click$ = new Subject<string>();

  @Input()
  services: Service[];

  @Input()
  form: FormGroup;

  constructor() {
  }

  ngOnInit() {
  }

  search = (text$: Observable<string>) => {
    const debouncedText$ = text$.pipe(debounceTime(200), distinctUntilChanged());
    const clicksWithClosedPopup$ = this.click$.pipe(filter(() => !this.instance.isPopupOpen()));
    const inputFocus$ = this.focus$;

    return merge(debouncedText$, inputFocus$, clicksWithClosedPopup$).pipe(
      map(term => (term === '' ? this.services.map(s => s.name)
        : this.services.map(s => s.name).filter(v => v.toLowerCase().indexOf(term.toLowerCase()) > -1)).slice(0, 10))
    );
  };

  clear() {
    this.model = undefined;
    this.form.get('service').setValue(undefined);
  }

  change($event: any) {
    const result = this.services.find(v => v.name === $event);
    if (result) {
      this.form.get('service').setValue(result.name);
    }
  }
}
