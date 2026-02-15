import { TestBed } from '@angular/core/testing';

import { SystemStatus } from './system-status.service';

describe('SystemStatus', () => {
  let service: SystemStatus;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(SystemStatus);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
