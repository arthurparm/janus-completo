import { Component } from '@angular/core';

@Component({
  selector: 'app-cpu-icon',
  standalone: true,
  template: `
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M9 3V5H7C5.9 5 5 5.9 5 7V9H3V11H5V13H3V15H5V17C5 18.1 5.9 19 7 19H9V21H11V19H13V21H15V19H17C18.1 19 19 18.1 19 17V15H21V13H19V11H21V9H19V7C19 5.9 18.1 5 17 5H15V3H13V5H11V3H9ZM7 15V9H17V15H7Z" fill="currentColor"/>
    </svg>
  `
})
export class CpuIconComponent {}