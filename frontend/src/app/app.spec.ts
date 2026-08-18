import { provideZonelessChangeDetection, signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { vi } from 'vitest';

import { App } from './app';
import { BackendAvailabilityService } from './core/services/backend-availability.service';

describe('App', () => {
  const snapshot = signal({
    state: 'available' as 'available' | 'degraded' | 'unreachable' | 'checking',
    checkedAt: null,
    detail: null,
  });
  const availability = {
    snapshot,
    hasIssue: () => snapshot().state !== 'available',
    isChecking: () => snapshot().state === 'checking',
    checkNow: vi.fn(() => Promise.resolve(true)),
  };

  beforeEach(async () => {
    snapshot.set({ state: 'available', checkedAt: null, detail: null });
    availability.checkNow.mockClear();
    await TestBed.configureTestingModule({
      imports: [App],
      providers: [
        provideZonelessChangeDetection(),
        { provide: BackendAvailabilityService, useValue: availability },
      ],
    }).compileComponents();
  });

  it('should create the app', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });

  it('should render skip link', () => {
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    const skipLink = compiled.querySelector('a.skip-link');
    expect(skipLink).toBeTruthy();
    expect(skipLink?.getAttribute('href')).toBe('#main-content');
  });

  it('shows a truthful unavailable state and runs an explicit retry', () => {
    snapshot.set({ state: 'unreachable', checkedAt: null, detail: null });
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();

    const alert = fixture.nativeElement.querySelector('[role="alert"]') as HTMLElement;
    const retry = alert.querySelector('button') as HTMLButtonElement;
    expect(alert.textContent).toContain('Backend Janus inacessível');
    expect(alert.textContent).not.toContain('MODO DEMONSTRAÇÃO');

    retry.click();
    expect(availability.checkNow).toHaveBeenCalledOnce();
  });
});
