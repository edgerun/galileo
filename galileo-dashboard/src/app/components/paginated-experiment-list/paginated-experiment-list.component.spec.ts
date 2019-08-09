import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { PaginatedExperimentListComponent } from './paginated-experiment-list.component';

describe('PaginatedExperimentListComponent', () => {
  let component: PaginatedExperimentListComponent;
  let fixture: ComponentFixture<PaginatedExperimentListComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ PaginatedExperimentListComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(PaginatedExperimentListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
