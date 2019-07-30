import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { SimpleExperimentListItemComponent } from './simple-experiment-list-item.component';

describe('SimpleExperimentListItemComponent', () => {
  let component: SimpleExperimentListItemComponent;
  let fixture: ComponentFixture<SimpleExperimentListItemComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ SimpleExperimentListItemComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(SimpleExperimentListItemComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
