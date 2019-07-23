import { TestBed } from '@angular/core/testing';

import { ExperimentService } from './experiment.service';

describe('ExperimentService', () => {
  beforeEach(() => TestBed.configureTestingModule({}));

  it('should be created', () => {
    const service: ExperimentService = TestBed.get(ExperimentService);
    expect(service).toBeTruthy();
  });
});
