import { Pipe, PipeTransform } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { MarkdownService } from '../services/markdown.service';

@Pipe({
    name: 'markdown',
    standalone: true
})
export class MarkdownPipe implements PipeTransform {

    constructor(
        private markdownService: MarkdownService,
        private sanitizer: DomSanitizer
    ) { }

    transform(value: string | object | null | undefined): SafeHtml {
        if (value === null || value === undefined) return '';

        let content = '';
        if (typeof value === 'string') {
            content = value;
        } else if (typeof value === 'object') {
            try {
                content = JSON.stringify(value, null, 2);
                content = '```json\n' + content + '\n```';
            } catch (e) {
                content = String(value);
            }
        } else {
            content = String(value);
        }

        const parsedHtml = this.markdownService.parse(content);
        // Trust the HTML because we already sanitized it with DOMPurify in the service
        return this.sanitizer.bypassSecurityTrustHtml(parsedHtml);
    }
}
