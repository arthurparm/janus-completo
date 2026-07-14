import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { RouterTestingModule } from '@angular/router/testing';

import { LearningWidget } from './learning-widget';

describe('LearningWidget', () => {
  let component: LearningWidget;
  let fixture: ComponentFixture<LearningWidget>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LearningWidget, HttpClientTestingModule, RouterTestingModule]
    })
    .compileComponents();

    fixture = TestBed.createComponent(LearningWidget);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('deve expor meta report como estado funcional quando nao houver licoes', () => {
    const summary = {
      lessons: [],
      meta_report: {
        overall_status: 'idle',
        health_score: 100,
        issues_detected: [],
        recommendations: [],
        summary: '',
      },
    };

    expect(component.hasLessons(summary)).toBe(false);
    expect(component.hasMetaReport(summary)).toBe(true);
    expect(component.getMetaStatus(summary)).toBe('idle');
    expect(component.getHealthScore(summary)).toBe(100);
    expect(component.getMetaSummary(summary)).toBe('Nenhuma falha detectada no ciclo mais recente.');
  });

  it('deve resumir issues e recomendacoes quando meta report tiver sinais operacionais', () => {
    const summary = {
      lessons: [],
      meta_report: {
        overall_status: 'attention',
        health_score: 82,
        issues_detected: ['fila lenta'],
        recommendations: ['verificar worker'],
      },
    };

    expect(component.getMetaSummary(summary)).toBe('1 issue(s), 1 recomendação(ões).');
  });
});
