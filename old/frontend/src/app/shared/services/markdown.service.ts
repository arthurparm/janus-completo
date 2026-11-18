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
        const defaultRenderer: any = new marked.Renderer();

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

        renderer.table = (...args: unknown[]) => {
            try {
                // Delegate to Marked's native renderer to stay compatible with v4/v5/v6 signatures.
                const rendered = String(defaultRenderer.table(...args) || '').trim();
                if (rendered) {
                    const withClasses = /<table[^>]*class=/i.test(rendered)
                        ? rendered
                        : rendered.replace(/<table>/i, '<table class="table table-striped">');
                    return `<div class="table-container">${withClasses}</div>`;
                }
            } catch {
                // Fallback to legacy signature handling below.
            }

            const header = typeof args[0] === 'string' ? args[0] : '';
            const body = typeof args[1] === 'string' ? args[1] : '';
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
            // Keep a narrow HTML allowlist because the output is rendered through [innerHTML].
            const cleanHtml = DOMPurify.sanitize(html, {
                ALLOWED_TAGS: [
                    'a', 'blockquote', 'br', 'code', 'div', 'em', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                    'hr', 'img', 'li', 'ol', 'p', 'pre', 'span', 'strong', 'table', 'tbody', 'td',
                    'th', 'thead', 'tr', 'ul'
                ],
                ALLOWED_ATTR: ['alt', 'class', 'href', 'src', 'target', 'rel'],
                ALLOW_UNKNOWN_PROTOCOLS: false,
                FORBID_TAGS: ['form', 'iframe', 'input', 'object', 'script', 'style', 'svg']
            });

            return cleanHtml;
        } catch (error) {
            this.logger.error('[MarkdownService] Markdown parsing error', error);
            return rawMarkdown; // Fail gentle or return error message
        }
    }
}
