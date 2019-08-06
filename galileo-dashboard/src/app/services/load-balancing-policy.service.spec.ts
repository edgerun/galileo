import { TestBed } from '@angular/core/testing';

import { LoadBalancingPolicyService } from './load-balancing-policy.service';

describe('LoadBalancingPolicyService', () => {
  beforeEach(() => TestBed.configureTestingModule({}));

  it('should be created', () => {
    const service: LoadBalancingPolicyService = TestBed.get(LoadBalancingPolicyService);
    expect(service).toBeTruthy();
  });
});
