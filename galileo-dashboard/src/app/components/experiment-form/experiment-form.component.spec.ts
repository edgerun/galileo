import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { ExperimentFormComponent } from './experiment-form.component';

describe('ExperimentFormComponent', () => {
  let component: ExperimentFormComponent;
  let fixture: ComponentFixture<ExperimentFormComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ ExperimentFormComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(ExperimentFormComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
