import { MarkdownPipe } from './markdown.pipe';
import { MarkdownService } from '../services/markdown.service';

describe('MarkdownPipe', () => {
  const logger = {
    error: vi.fn()
  };

  const createService = () => new MarkdownService(logger as never);

  const createPipe = () =>
    new (MarkdownPipe as unknown as new (...args: unknown[]) => MarkdownPipe)(
      createService(),
      undefined
    );

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns a sanitized html string instead of a trusted html wrapper', () => {
    const pipe = createPipe();

    const result = pipe.transform('Hello <script>alert(1)</script>');

    expect(typeof result).toBe('string');
    expect(result).toContain('Hello');
    expect(result).not.toContain('<script>');
  });

  it('renders object values as formatted json code blocks', () => {
    const pipe = createPipe();

    const result = pipe.transform({ answer: 42, ok: true }) as string;

    expect(result).toContain('language-json');
    expect(result).toContain('hljs-attr');
    expect(result).toContain('"answer"');
    expect(result).toContain('42');
  });
});
