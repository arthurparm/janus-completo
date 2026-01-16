import { ComponentFixture, TestBed } from '@angular/core/testing'
import { SkeletonComponent } from './skeleton.component'

describe('SkeletonComponent', () => {
  let component: SkeletonComponent
  let fixture: ComponentFixture<SkeletonComponent>

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SkeletonComponent]
    }).compileComponents()

    fixture = TestBed.createComponent(SkeletonComponent)
    component = fixture.componentInstance
    fixture.detectChanges()
  })

  it('should create', () => {
    expect(component).toBeTruthy()
  })

  describe('default values', () => {
    it('should have default variant as text', () => {
      expect(component.variant).toBe('text')
    })

    it('should have default count as 1', () => {
      expect(component.count).toBe(1)
    })

    it('should have default animated as true', () => {
      expect(component.animated).toBe(true)
    })

    it('should have default rounded as false', () => {
      expect(component.rounded).toBe(false)
    })
  })

  describe('counter', () => {
    it('should return array with correct length', () => {
      component.count = 3
      const counter = component.counter
      
      expect(counter.length).toBe(3)
      expect(counter).toEqual([0, 1, 2])
    })

    it('should return empty array when count is 0', () => {
      component.count = 0
      const counter = component.counter
      
      expect(counter.length).toBe(0)
      expect(counter).toEqual([])
    })
  })

  describe('getWidth', () => {
    it('should return pixel value for number input', () => {
      component.width = 100
      expect(component.getWidth()).toBe('100px')
    })

    it('should return string value for string input', () => {
      component.width = '50%'
      expect(component.getWidth()).toBe('50%')
    })

    it('should return auto when width is undefined', () => {
      component.width = undefined
      expect(component.getWidth()).toBe('auto')
    })
  })

  describe('getHeight', () => {
    it('should return pixel value for number input', () => {
      component.height = 50
      expect(component.getHeight()).toBe('50px')
    })

    it('should return string value for string input', () => {
      component.height = '100vh'
      expect(component.getHeight()).toBe('100vh')
    })

    it('should return auto when height is undefined', () => {
      component.height = undefined
      expect(component.getHeight()).toBe('auto')
    })
  })

  describe('CSS classes', () => {
    it('should apply correct CSS classes based on variant', () => {
      const variants = ['text', 'rect', 'circle', 'avatar', 'button', 'card', 'paragraph']
      
      variants.forEach(variant => {
        fixture.componentRef.setInput('variant', variant as any)
        fixture.detectChanges()
        
        const skeletonElement = fixture.nativeElement.querySelector('.skeleton')
        expect(skeletonElement).toHaveClass(`skeleton-${variant}`)
      })
    })

    it('should apply rounded class when rounded is true', () => {
      fixture.componentRef.setInput('rounded', true)
      fixture.detectChanges()
      
      const skeletonElement = fixture.nativeElement.querySelector('.skeleton')
      expect(skeletonElement).toHaveClass('rounded')
    })

    it('should apply animated class when animated is true', () => {
      fixture.componentRef.setInput('animated', true)
      fixture.detectChanges()
      
      const wrapperElement = fixture.nativeElement.querySelector('.skeleton-wrapper')
      expect(wrapperElement).toHaveClass('animated')
    })
  })

  describe('template rendering', () => {
    it('should render correct number of skeleton elements', () => {
      fixture.componentRef.setInput('count', 3)
      fixture.componentRef.setInput('variant', 'card')
      fixture.detectChanges()
      
      const skeletonElements = fixture.nativeElement.querySelectorAll('.skeleton')
      expect(skeletonElements.length).toBe(3)
    })

    it('should apply custom styles when width and height are provided', () => {
      fixture.componentRef.setInput('width', 200)
      fixture.componentRef.setInput('height', 100)
      fixture.detectChanges()
      
      const skeletonElement = fixture.nativeElement.querySelector('.skeleton')
      expect(skeletonElement.style.width).toBe('200px')
      expect(skeletonElement.style.height).toBe('100px')
    })
  })
})
