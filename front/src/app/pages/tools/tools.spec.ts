import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TranslateLoader, TranslateModule, TranslateService } from '@ngx-translate/core';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { ToolsComponent } from './tools';
import { of } from 'rxjs';

describe('ToolsPage', () => {
  let component: ToolsComponent;
  let fixture: ComponentFixture<ToolsComponent>;
  const translations = {
    NAV: {
      TOOLS: 'Ferramentas'
    },
    COMMON: {
      LOADING: 'Carregando...'
    }
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        ToolsComponent,
        TranslateModule.forRoot({
          defaultLanguage: 'pt-BR',
          loader: {
            provide: TranslateLoader,
            useValue: {
              getTranslation: () => of(translations)
            }
          }
        })
      ],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting()
      ]
    })
    .compileComponents();

    const translate = TestBed.inject(TranslateService);
    translate.setTranslation('pt-BR', translations);
    translate.setDefaultLang('pt-BR');
    translate.use('pt-BR');

    fixture = TestBed.createComponent(ToolsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should render page title', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('h1')?.textContent).toContain('Ferramentas');
  });
});
