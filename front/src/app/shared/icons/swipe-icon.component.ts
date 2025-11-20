import { Component } from '@angular/core';

@Component({
  selector: 'app-swipe-icon',
  standalone: true,
  template: `
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M4 15H7V20H4V15ZM20 9H17V4H20V9ZM4 20C4 21.1 4.9 22 6 22H18C19.1 22 20 21.1 20 20H4ZM13 20H11V12L7.5 15.5L9 17L12 14L15 17L16.5 15.5L13 12V20ZM20 8C20 6.9 19.1 6 18 6H17V9H20V8Z" fill="currentColor"/>
    </svg>
  `
})
export class SwipeIconComponent {}