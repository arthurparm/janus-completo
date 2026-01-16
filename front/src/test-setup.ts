import '@angular/compiler'
import '@analogjs/vitest-angular/setup-snapshots'
import { setupTestBed } from '@analogjs/vitest-angular/setup-testbed'
import '@testing-library/jest-dom/vitest'
import { vi } from 'vitest'
import { of } from 'rxjs'

vi.mock('@angular/fire/auth', () => ({
  Auth: class {},
  GoogleAuthProvider: class {},
  signInAnonymously: vi.fn(),
  signInWithPopup: vi.fn(),
  signInWithEmailAndPassword: vi.fn(),
  signOut: vi.fn()
}))

vi.mock('@angular/fire/database', () => ({
  Database: class {},
  ref: vi.fn(),
  objectVal: vi.fn(() => of({}))
}))

setupTestBed()
