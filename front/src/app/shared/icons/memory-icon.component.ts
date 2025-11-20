import { Component } from '@angular/core';

@Component({
  selector: 'app-memory-icon',
  standalone: true,
  template: `
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M17 1H7C5.9 1 5 1.9 5 3V21C5 22.1 5.9 23 7 23H17C18.1 23 19 22.1 19 21V3C19 1.9 18.1 1 17 1ZM17 19H7V17H17V19ZM17 13H7V11H17V13ZM17 7H7V5H17V7Z" fill="currentColor"/>
    </svg>
  `
})
export class MemoryIconComponent {}