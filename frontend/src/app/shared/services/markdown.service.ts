import { Injectable } from '@angular/core';
import { marked } from 'marked';
import { default as DOMPurify } from 'dompurify';
import hljs from 'highlight.js';
import { AppLoggerService } from '../../core/services/app-logger.service';

@Injectable({
    providedIn: 'root'
})
export class MarkdownService {

    constructor(private readonly logger: AppLoggerService) {
        this.configureMarked();
    }

    private configureMarked(): void {
        // Custom renderer for robust code block handling
        const renderer: any = new marked.Renderer();

        renderer.code = (text: string, lang: string) => {
            const validLang = lang && hljs.getLanguage(lang) ? lang : 'plaintext';
            try {
                const highlighted = hljs.highlight(text, { language: validLang }).value;
                return `<div class="code-block-wrapper">
                   <div class="code-header">
                     <span class="lang-label">${validLang}</span>
                   </div>
                   <pre><code class="hljs language-${validLang}">${highlighted}</code></pre>
                 </div>`;
            } catch (e) {
                return `<pre><code>${text}</code></pre>`;
            }
        };

        renderer.table = (header: string, body: string) => {
            return `<div class="table-container"><table class="table table-striped">
                    <thead>${header}</thead>
                    <tbody>${body}</tbody>
                </table></div>`;
        };

        marked.setOptions({
            renderer,
            gfm: true,
            breaks: true
        });
    }

    /**
     * Parses markdown text to safe HTML
     * @param rawMarkdown The markdown string from LLM
     * @returns Sanitized HTML string
     */
    public parse(rawMarkdown: string): string {
        if (!rawMarkdown) return '';

        try {
            const html = marked.parse(rawMarkdown) as string;
            // Sanitize specifically allowing standard formatting tags and our custom code classes
            const cleanHtml = DOMPurify.sanitize(html, {
                ADD_TAGS: ['img', 'pre', 'code', 'table', 'thead', 'tbody', 'tr', 'td', 'th', 'div', 'span'],
                ADD_ATTR: ['class', 'src', 'alt', 'href', 'target']
            });

            return cleanHtml;
        } catch (error) {
            this.logger.error('[MarkdownService] Markdown parsing error', error);
            return rawMarkdown; // Fail gentle or return error message
        }
    }
}
