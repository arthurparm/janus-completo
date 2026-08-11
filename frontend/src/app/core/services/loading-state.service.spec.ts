import { TestBed } from '@angular/core/testing'
import { LoadingStateService } from './loading-state.service'
import { LoadingConfig } from '../types'

describe('LoadingStateService', () => {
  let service: LoadingStateService

  beforeEach(() => {
    vi.useFakeTimers()
    TestBed.configureTestingModule({})
    service = TestBed.inject(LoadingStateService)
  })

  afterEach(() => {
    vi.useRealTimers()
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
    it('should stop loading and update state', () => {
      service.startLoading('test-key')
      expect(service.isKeyLoading('test-key')).toBe(true)
      
      service.stopLoading('test-key')
      
      // Should still be loading immediately after stop
      expect(service.isKeyLoading('test-key')).toBe(false)
      
      // State should be removed after delay
      vi.advanceTimersByTime(300)
      expect(service.getLoadingState('test-key')).toBeUndefined()
      expect(service.isLoading()).toBe(false)
    })

    it('should update global loading state', () => {
      service.startLoading('key1', { global: true })
      service.startLoading('key2', { global: true })
      
      expect(service.isGlobalLoading()).toBe(true)
      
      service.stopLoading('key1')
      expect(service.isGlobalLoading()).toBe(true) // Still have key2
      vi.advanceTimersByTime(300)
      expect(service.isGlobalLoading()).toBe(true)

      service.stopLoading('key2')
      expect(service.isGlobalLoading()).toBe(false)
      vi.advanceTimersByTime(300)
      expect(service.isGlobalLoading()).toBe(false)
    })

    it('should not remove a loading state restarted before the cleanup delay', () => {
      service.startLoading('test-key')
      service.stopLoading('test-key')
      vi.advanceTimersByTime(100)

      service.startLoading('test-key')
      vi.advanceTimersByTime(200)

      expect(service.isKeyLoading('test-key')).toBe(true)
      expect(service.getLoadingState('test-key')).toBeDefined()
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
    it('should force stop all active loadings', () => {
      service.startLoading('key1')
      service.startLoading('key2')
      
      expect(service.isLoading()).toBe(true)
      
      service.forceStopAll()
      
      expect(service.isLoading()).toBe(false)
      expect(service.loadingKeys()).toEqual([])
      vi.advanceTimersByTime(300)
      expect(service.isLoading()).toBe(false)
      expect(service.loadingKeys()).toEqual([])
    })

    it('should preserve loading states started during the cleanup delay', () => {
      service.startLoading('old-key')
      service.forceStopAll()
      vi.advanceTimersByTime(100)

      service.startLoading('new-key', { global: true, http: true })
      vi.advanceTimersByTime(200)

      expect(service.getLoadingState('old-key')).toBeUndefined()
      expect(service.isKeyLoading('new-key')).toBe(true)
      expect(service.isGlobalLoading()).toBe(true)
      expect(service.isHttpLoading()).toBe(true)
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
