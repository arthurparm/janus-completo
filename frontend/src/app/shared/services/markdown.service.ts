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

        renderer.code = (code: unknown, languageHint?: string) => {
            let text = '';
            let lang = '';

            if (typeof code === 'string') {
                text = code;
                lang = languageHint || '';
            } else if (code && typeof code === 'object') {
                const maybeToken = code as { text?: unknown; lang?: unknown; language?: unknown; raw?: unknown };
                if (typeof maybeToken.text === 'string') {
                    text = maybeToken.text;
                } else if (typeof maybeToken.raw === 'string') {
                    text = maybeToken.raw;
                } else {
                    try {
                        text = JSON.stringify(maybeToken, null, 2);
                    } catch {
                        text = String(maybeToken);
                    }
                }

                if (typeof maybeToken.lang === 'string') lang = maybeToken.lang;
                else if (typeof maybeToken.language === 'string') lang = maybeToken.language;
                else lang = languageHint || '';
            } else {
                text = String(code ?? '');
                lang = languageHint || '';
            }

            const normalizedText = String(text || '').replace(/\[\s*object\s+object\s*\]/gi, '').trimEnd();
            const validLang = lang && hljs.getLanguage(lang) ? lang : 'plaintext';
            try {
                const highlighted = hljs.highlight(normalizedText, { language: validLang }).value;
                return `<div class="code-block-wrapper">
                   <div class="code-header">
                     <span class="lang-label">${validLang}</span>
                   </div>
                   <pre><code class="hljs language-${validLang}">${highlighted}</code></pre>
                 </div>`;
            } catch (e) {
                return `<pre><code>${normalizedText}</code></pre>`;
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
