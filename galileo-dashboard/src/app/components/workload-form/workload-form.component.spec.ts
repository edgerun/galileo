import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { WorkloadFormComponent } from './workload-form.component';

describe('WorkloadFormComponent', () => {
  let component: WorkloadFormComponent;
  let fixture: ComponentFixture<WorkloadFormComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ WorkloadFormComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(WorkloadFormComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
