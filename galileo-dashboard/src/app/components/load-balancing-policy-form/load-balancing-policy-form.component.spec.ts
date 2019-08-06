import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { LoadBalancingPolicyFormComponent } from './load-balancing-policy-form.component';

describe('LoadBalancingPolicyFormComponent', () => {
  let component: LoadBalancingPolicyFormComponent;
  let fixture: ComponentFixture<LoadBalancingPolicyFormComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ LoadBalancingPolicyFormComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(LoadBalancingPolicyFormComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
