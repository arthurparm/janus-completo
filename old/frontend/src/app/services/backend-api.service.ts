import { Injectable } from '@angular/core'

import { ApiContextService } from './api-context.service'
import { AutonomyApiService } from './domain/autonomy-api-service'
import { ChatApiService } from './domain/chat-api-service'
import { ContextApiService } from './domain/context-api-service'
import { DocumentsApiService } from './domain/documents-api-service'
import { ExperimentApiService } from './domain/experiment-api-service'
import { FeedbackApiService } from './domain/feedback-api-service'
import { GraphApiService } from './domain/graph-api-service'
import { KnowledgeApiService } from './domain/knowledge-api-service'
import { LlmApiService } from './domain/llm-api-service'
import { MemoryApiService } from './domain/memory-api-service'
import { ObservabilityApiService } from './domain/observability-api-service'
import { ProductivityApiService } from './domain/productivity-api-service'
import { SystemApiService } from './domain/system-api-service'
import { ToolsApiService } from './domain/tools-api-service'
import { UsersApiService } from './domain/users-api-service'
import { WebRTCApiService } from './domain/web-rtcapi-service'

@Injectable({ providedIn: 'root' })
export class BackendApiService {
  constructor(
    public readonly context: ApiContextService,
    public readonly system: SystemApiService,
    public readonly chat: ChatApiService,
    public readonly knowledge: KnowledgeApiService,
    public readonly documents: DocumentsApiService,
    public readonly autonomy: AutonomyApiService,
    public readonly observability: ObservabilityApiService,
    public readonly tools: ToolsApiService,
    public readonly webrtc: WebRTCApiService,
    public readonly llm: LlmApiService,
    public readonly memory: MemoryApiService,
    public readonly productivity: ProductivityApiService,
    public readonly users: UsersApiService,
    public readonly ctx: ContextApiService,
    public readonly experiments: ExperimentApiService,
    public readonly graph: GraphApiService,
    public readonly feedback: FeedbackApiService
  ) {}
}

