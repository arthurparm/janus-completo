import { Component } from '@angular/core';

@Component({
  selector: 'app-network-icon',
  standalone: true,
  template: `
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M1 9L2 10L5 7L8 10L11 7L14 10L17 7L20 10L21 9L12 2L3 9ZM12 4.8L16.2 8H7.8L12 4.8ZM5 16V18H19V16H5ZM5 12V14H19V12H5Z" fill="currentColor"/>
    </svg>
  `
})
export class NetworkIconComponent {}