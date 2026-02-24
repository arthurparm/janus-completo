import { Component } from '@angular/core'
import { ComponentFixture, TestBed } from '@angular/core/testing'
import { LoadingComponent } from './loading.component'
import { LoadingStateService } from '../../../core/services/loading-state.service'

class MockLoadingStateService {
  private loadingStates = new Map<string, any>()

  isKeyLoading(key: string): boolean {
    return this.loadingStates.has(key) && this.loadingStates.get(key).isLoading
  }

  getLoadingState(key: string): any {
    return this.loadingStates.get(key)
  }

  startLoading(key: string, config?: any): void {
    this.loadingStates.set(key, { isLoading: true, ...config })
  }

  stopLoading(key: string): void {
    if (this.loadingStates.has(key)) {
      this.loadingStates.get(key).isLoading = false
    }
  }
}

@Component({
  standalone: true,
  imports: [LoadingComponent],
  template: `<app-loading [isLoading]="isLoading">Projected content</app-loading>`
})
class LoadingHostComponent {
  isLoading = false
}

describe('LoadingComponent', () => {
  let component: LoadingComponent
  let fixture: ComponentFixture<LoadingComponent>
  let loadingStateService: MockLoadingStateService

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LoadingComponent, LoadingHostComponent],
      providers: [
        { provide: LoadingStateService, useClass: MockLoadingStateService }
      ]
    }).compileComponents()

    fixture = TestBed.createComponent(LoadingComponent)
    component = fixture.componentInstance
    loadingStateService = TestBed.inject(LoadingStateService) as any
    fixture.detectChanges()
  })

  it('should create', () => {
    expect(component).toBeTruthy()
  })

  describe('default values', () => {
    it('should have default isLoading as false', () => {
      expect(component.isLoading).toBe(false)
    })

    it('should have default message as empty string', () => {
      expect(component.message).toBe('')
    })

    it('should have default diameter as 40', () => {
      expect(component.diameter).toBe(40)
    })

    it('should have default color as primary', () => {
      expect(component.color).toBe('primary')
    })

    it('should have default mode as indeterminate', () => {
      expect(component.mode).toBe('indeterminate')
    })

    it('should have default overlay as false', () => {
      expect(component.overlay).toBe(false)
    })

    it('should have default showSpinner as true', () => {
      expect(component.showSpinner).toBe(true)
    })

    it('should have default showMessage as true', () => {
      expect(component.showMessage).toBe(true)
    })
  })

  describe('actualLoading', () => {
    it('should return isLoading when loadingKey is not provided', () => {
      component.isLoading = true
      expect(component.actualLoading).toBe(true)

      component.isLoading = false
      expect(component.actualLoading).toBe(false)
    })

    it('should return loading state from service when loadingKey is provided', () => {
      component.loadingKey = 'test-key'
      component.isLoading = false

      loadingStateService.startLoading('test-key')
      expect(component.actualLoading).toBe(true)

      loadingStateService.stopLoading('test-key')
      expect(component.actualLoading).toBe(false)
    })
  })

  describe('actualMessage', () => {
    it('should return message when loadingKey is not provided', () => {
      component.message = 'Test message'
      expect(component.actualMessage).toBe('Test message')
    })

    it('should return message from service when loadingKey is provided', () => {
      component.loadingKey = 'test-key'
      component.message = 'Default message'

      loadingStateService.startLoading('test-key', { message: 'Service message' })
      expect(component.actualMessage).toBe('Service message')

      loadingStateService.stopLoading('test-key')
      expect(component.actualMessage).toBe('Service message')
    })
  })

  describe('template rendering', () => {
    it('should show loading container when actualLoading is true', () => {
      fixture.componentRef.setInput('isLoading', true)
      fixture.detectChanges()

      const loadingContainer = fixture.nativeElement.querySelector('.loading-container')
      expect(loadingContainer).toBeTruthy()
    })

    it('should hide loading container when actualLoading is false', () => {
      component.isLoading = false
      fixture.detectChanges()

      const loadingContainer = fixture.nativeElement.querySelector('.loading-container')
      expect(loadingContainer).toBeFalsy()
    })

    it('should show spinner when showSpinner is true', () => {
      fixture.componentRef.setInput('isLoading', true)
      fixture.componentRef.setInput('showSpinner', true)
      fixture.detectChanges()

      const spinner = fixture.nativeElement.querySelector('ui-spinner')
      expect(spinner).toBeTruthy()
    })

    it('should hide spinner when showSpinner is false', () => {
      fixture.componentRef.setInput('isLoading', true)
      fixture.componentRef.setInput('showSpinner', false)
      fixture.detectChanges()

      const spinner = fixture.nativeElement.querySelector('ui-spinner')
      expect(spinner).toBeFalsy()
    })

    it('should show message when showMessage and actualMessage are truthy', () => {
      fixture.componentRef.setInput('isLoading', true)
      fixture.componentRef.setInput('showMessage', true)
      fixture.componentRef.setInput('message', 'Loading message')
      fixture.detectChanges()

      const messageElement = fixture.nativeElement.querySelector('.loading-message')
      expect(messageElement).toBeTruthy()
      expect(messageElement.textContent).toContain('Loading message')
    })

    it('should hide message when showMessage is false', () => {
      fixture.componentRef.setInput('isLoading', true)
      fixture.componentRef.setInput('showMessage', false)
      fixture.componentRef.setInput('message', 'Loading message')
      fixture.detectChanges()

      const messageElement = fixture.nativeElement.querySelector('.loading-message')
      expect(messageElement).toBeFalsy()
    })

    it('should apply overlay class when overlay is true', () => {
      fixture.componentRef.setInput('isLoading', true)
      fixture.componentRef.setInput('overlay', true)
      fixture.detectChanges()

      const loadingContainer = fixture.nativeElement.querySelector('.loading-container')
      expect(loadingContainer).toHaveClass('overlay')
    })

    it('should render projected content when not loading', () => {
      const hostFixture = TestBed.createComponent(LoadingHostComponent)
      hostFixture.detectChanges()

      expect(hostFixture.nativeElement.textContent).toContain('Projected content')
    })
  })
})
