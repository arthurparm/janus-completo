import { Component } from '@angular/core';

@Component({
  selector: 'app-storage-icon',
  standalone: true,
  template: `
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M18 2H6C4.9 2 4 2.9 4 4V20C4 21.1 4.9 22 6 22H18C19.1 22 20 21.1 20 20V4C20 2.9 19.1 2 18 2ZM18 20H6V16H18V20ZM18 12H6V8H18V12Z" fill="currentColor"/>
    </svg>
  `
})
export class StorageIconComponent {}