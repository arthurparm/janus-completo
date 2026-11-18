import { MarkdownService } from './markdown.service';

describe('MarkdownService', () => {
  const logger = {
    error: vi.fn()
  };

  const createService = () => new MarkdownService(logger as never);

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('removes script tags and inline event handlers from rendered html', () => {
    const service = createService();

    const result = service.parse('Hello <img src="x" onerror="alert(1)"><script>alert(1)</script>');

    expect(result).toContain('Hello');
    expect(result).toContain('<img src="x">');
    expect(result).not.toContain('onerror');
    expect(result).not.toContain('<script>');
  });

  it('removes javascript urls from markdown links', () => {
    const service = createService();

    const result = service.parse('[click me](javascript:alert(1))');

    expect(result).toContain('click me');
    expect(result).not.toContain('javascript:alert(1)');
  });

  it('preserves code blocks and tables for legitimate markdown', () => {
    const service = createService();

    const result = service.parse('```ts\nconst value = 1;\n```\n\n|a|b|\n|-|-|\n|1|2|');

    expect(result).toContain('code-block-wrapper');
    expect(result).toContain('language-ts');
    expect(result).toContain('<table');
    expect(result).toContain('hljs-keyword');
  });
});
