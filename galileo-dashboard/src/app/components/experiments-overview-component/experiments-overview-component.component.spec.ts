import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { ExperimentsOverviewComponentComponent } from './experiments-overview-component.component';

describe('ExperimentsOverviewComponentComponent', () => {
  let component: ExperimentsOverviewComponentComponent;
  let fixture: ComponentFixture<ExperimentsOverviewComponentComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ ExperimentsOverviewComponentComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(ExperimentsOverviewComponentComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
