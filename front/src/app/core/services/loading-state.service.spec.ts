import { TestBed } from '@angular/core/testing'
import { LoadingStateService } from './loading-state.service'
import { LoadingConfig } from '../types'

describe('LoadingStateService', () => {
  let service: LoadingStateService

  beforeEach(() => {
    TestBed.configureTestingModule({})
    service = TestBed.inject(LoadingStateService)
  })

  it('should be created', () => {
    expect(service).toBeTruthy()
  })

  describe('startLoading', () => {
    it('should start loading with default config', () => {
      service.startLoading('test-key')

      expect(service.isKeyLoading('test-key')).toBe(true)
      expect(service.isLoading()).toBe(true)

      const state = service.getLoadingState('test-key')
      expect(state?.isLoading).toBe(true)
      expect(state?.timestamp).toBeDefined()
    })

    it('should start loading with custom config', () => {
      const config: LoadingConfig = {
        message: 'Test message',
        progress: 50,
        global: true,
        http: true
      }

      service.startLoading('test-key', config)

      const state = service.getLoadingState('test-key')
      expect(state?.message).toBe('Test message')
      expect(state?.progress).toBe(50)
      expect(service.isGlobalLoading()).toBe(true)
      expect(service.isHttpLoading()).toBe(true)
    })
  })

  describe('stopLoading', () => {
    it('should stop loading and update state', (done) => {
      service.startLoading('test-key')
      expect(service.isKeyLoading('test-key')).toBe(true)

      service.stopLoading('test-key')

      // Should still be loading immediately after stop
      expect(service.isKeyLoading('test-key')).toBe(false)

      // State should be removed after delay
      setTimeout(() => {
        expect(service.getLoadingState('test-key')).toBeUndefined()
        expect(service.isLoading()).toBe(false)
        done()
      }, 400)
    })

    it('should update global loading state', (done) => {
      service.startLoading('key1', { global: true })
      service.startLoading('key2', { global: true })

      expect(service.isGlobalLoading()).toBe(true)

      service.stopLoading('key1')
      expect(service.isGlobalLoading()).toBe(true) // Still have key2

      service.stopLoading('key2')

      setTimeout(() => {
        expect(service.isGlobalLoading()).toBe(false)
        done()
      }, 400)
    })
  })

  describe('updateProgress', () => {
    it('should update progress for existing loading state', () => {
      service.startLoading('test-key')

      service.updateProgress('test-key', 75)

      const state = service.getLoadingState('test-key')
      expect(state?.progress).toBe(75)
    })

    it('should not update progress for non-existing key', () => {
      service.updateProgress('non-existing', 100)

      expect(service.getLoadingState('non-existing')).toBeUndefined()
    })
  })

  describe('updateMessage', () => {
    it('should update message for existing loading state', () => {
      service.startLoading('test-key')

      service.updateMessage('test-key', 'New message')

      const state = service.getLoadingState('test-key')
      expect(state?.message).toBe('New message')
    })

    it('should not update message for non-existing key', () => {
      service.updateMessage('non-existing', 'New message')

      expect(service.getLoadingState('non-existing')).toBeUndefined()
    })
  })

  describe('clearAll', () => {
    it('should clear all loading states', () => {
      service.startLoading('key1')
      service.startLoading('key2')
      service.startLoading('key3', { global: true, http: true })

      expect(service.isLoading()).toBe(true)
      expect(service.isGlobalLoading()).toBe(true)
      expect(service.isHttpLoading()).toBe(true)

      service.clearAll()

      expect(service.isLoading()).toBe(false)
      expect(service.isGlobalLoading()).toBe(false)
      expect(service.isHttpLoading()).toBe(false)
      expect(service.loadingKeys()).toEqual([])
    })
  })

  describe('forceStopAll', () => {
    it('should force stop all active loadings', (done) => {
      service.startLoading('key1')
      service.startLoading('key2')

      expect(service.isLoading()).toBe(true)

      service.forceStopAll()

      setTimeout(() => {
        expect(service.isLoading()).toBe(false)
        expect(service.loadingKeys()).toEqual([])
        done()
      }, 400)
    })
  })

  describe('loadingKeys', () => {
    it('should return only active loading keys', () => {
      service.startLoading('key1')
      service.startLoading('key2')
      service.stopLoading('key1')

      const keys = service.loadingKeys()
      expect(keys).toEqual(['key2'])
    })
  })
})
