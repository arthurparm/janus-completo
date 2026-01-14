import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
    selector: 'app-ui-citation-card',
    standalone: true,
    imports: [CommonModule],
    template: `
    <div class="citation-card" [class.expanded]="expanded">
      <div class="citation-header" (click)="toggle()">
        <div class="file-info">
          <span class="icon">{{ getIcon() }}</span>
          <span class="path">{{ citation.file_path || citation.doc_id || 'Unknown Source' }}</span>
        </div>
        <div class="meta-info">
          <span class="score" *ngIf="citation.score">{{ (citation.score * 100) | number:'1.0-0' }}% match</span>
          <span class="toggle-icon">{{ expanded ? 'expand_less' : 'expand_more' }}</span>
        </div>
      </div>
      
      <div class="citation-body" *ngIf="expanded">
        <div class="snippet-code">
          <code>{{ citation.snippet || 'No text content available.' }}</code>
        </div>
      </div>
    </div>
  `,
    styleUrls: ['./ui-citation-card.component.scss']
})
export class UiCitationCardComponent {
    @Input() citation: any; // Type as needed
    expanded = false;

    toggle() {
        this.expanded = !this.expanded;
    }

    getIcon(): string {
        const type = this.citation.type || '';
        if (type.includes('code') || this.citation.file_path?.endsWith('ts') || this.citation.file_path?.endsWith('py')) return 'code';
        if (type.includes('doc') || type.includes('pdf')) return 'description';
        return 'article';
    }
}
