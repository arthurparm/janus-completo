import { Component, OnInit, inject, ChangeDetectorRef, ViewChild, ElementRef } from '@angular/core'
import { DemoService } from '../../core/services/demo.service'
import { AuthService } from '../../core/auth/auth.service'
import { CommonModule } from '@angular/common'
import { FormsModule } from '@angular/forms'
import { JanusApiService, DocSearchResponse, DocSearchResultItem, DocListResponse, UploadResponse, DocListItem } from '../../services/janus-api.service'
import { MatIconModule } from '@angular/material/icon'

export type SearchResult = DocSearchResultItem;

@Component({
    selector: 'app-documents',
    standalone: true,
    imports: [CommonModule, FormsModule, MatIconModule],
    templateUrl: './documents.html',
    styleUrl: './documents.scss'
})
export class DocumentsComponent implements OnInit {
    @ViewChild('fileInput') fileInput!: ElementRef<HTMLInputElement>

    private api = inject(JanusApiService)
    public auth = inject(AuthService)
    private cdr = inject(ChangeDetectorRef)

    documents: DocListItem[] = []
    searchResults: SearchResult[] = []

    get totalChunks(): number {
        return this.documents.reduce((acc, doc) => acc + (doc.chunks || 0), 0)
    }

    loading = false
    uploading = false
    searching = false
    error: string | null = null
    successMessage: string | null = null

    // Search
    searchQuery = ''
    minScore = 0.5

    // Upload
    urlToLink = ''
    uploadProgress = 0

    private demoService = inject(DemoService)

    get isOffline() {
        return this.demoService.isOffline()
    }

    ngOnInit() {
        this.loadDocuments()
    }

    loadDocuments() {
        this.loading = true
        this.error = null

        // Stop if offline
        if (this.demoService.isOffline()) {
            this.loading = false
            this.documents = []
            return
        }

        const userId = this.auth.currentUserValue?.id
        this.api.listDocuments(undefined, userId).subscribe({
            next: (response: DocListResponse) => {
                this.documents = response.items || []
                this.loading = false
                this.cdr.detectChanges()
            },
            error: (err: unknown) => {
                console.error('Error loading documents:', err)
                const status = (err as { status?: number })?.status;
                if (status === 0 || status === 504) {
                    this.demoService.enableOfflineMode();
                    this.loading = false
                    this.documents = []
                } else {
                    this.error = 'Falha ao carregar documentos'
                    this.loading = false
                }
                this.cdr.detectChanges()
            }
        })
    }

    triggerFileSelect() {
        this.fileInput.nativeElement.click()
    }

    onFileSelected(event: Event) {
        const input = event.target as HTMLInputElement
        if (!input.files?.length) return

        const file = input.files[0]
        this.uploadFile(file)
        input.value = '' // Reset for future uploads
    }

    uploadFile(file: File) {
        this.uploading = true
        this.uploadProgress = 0
        this.error = null
        this.successMessage = null

        const userId = this.auth.currentUserValue?.id
        this.api.uploadDocument(file, undefined, userId).subscribe({
            next: (event: { progress?: number; response?: UploadResponse }) => {
                if (event.progress !== undefined) {
                    this.uploadProgress = event.progress
                    this.cdr.detectChanges()
                }
                if (event.response) {
                    this.uploading = false
                    this.uploadProgress = 100
                    this.successMessage = `Documento "${file.name}" indexado com ${event.response.chunks} chunks`
                    this.loadDocuments()
                    setTimeout(() => {
                        this.successMessage = null
                        this.cdr.detectChanges()
                    }, 5000)
                }
            },
            error: (err: unknown) => {
                console.error('Upload error:', err)
                this.error = 'Falha ao enviar documento'
                this.uploading = false
                this.cdr.detectChanges()
            }
        })
    }

    linkUrl() {
        if (!this.urlToLink.trim()) return

        this.uploading = true
        this.error = null
        this.successMessage = null

        const userId = this.auth.currentUserValue?.id
        this.api.linkUrl('', this.urlToLink, userId).subscribe({
            next: (response: UploadResponse) => {
                this.uploading = false
                this.successMessage = `URL indexada com ${response.chunks} chunks`
                this.urlToLink = ''
                this.loadDocuments()
                setTimeout(() => {
                    this.successMessage = null
                    this.cdr.detectChanges()
                }, 5000)
            },
            error: (err: unknown) => {
                console.error('Link URL error:', err)
                this.error = 'Falha ao indexar URL'
                this.uploading = false
                this.cdr.detectChanges()
            }
        })
    }

    search() {
        if (!this.searchQuery.trim()) return

        this.searching = true
        this.searchResults = []
        this.error = null

        this.api.searchDocuments(this.searchQuery, this.minScore).subscribe({
            next: (response: DocSearchResponse) => {
                this.searchResults = response.results || []
                this.searching = false
                this.cdr.detectChanges()
            },
            error: (err: unknown) => {
                console.error('Search error:', err)
                this.error = 'Falha na busca'
                this.searching = false
                this.cdr.detectChanges()
            }
        })
    }

    deleteDocument(doc: DocListItem) {
        if (!confirm(`Excluir documento "${doc.file_name || doc.doc_id}"?`)) return

        this.api.deleteDocument(doc.doc_id).subscribe({
            next: () => {
                this.successMessage = 'Documento excluído'
                this.loadDocuments()
                setTimeout(() => {
                    this.successMessage = null
                    this.cdr.detectChanges()
                }, 3000)
            },
            error: (err: unknown) => {
                console.error('Delete error:', err)
                this.error = 'Falha ao excluir documento'
                this.cdr.detectChanges()
            }
        })
    }

    clearSearch() {
        this.searchQuery = ''
        this.searchResults = []
    }

    formatDate(timestamp?: number): string {
        if (!timestamp) return 'N/A'
        return new Date(timestamp).toLocaleDateString('pt-BR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        })
    }

    getFileIcon(fileName?: string): string {
        if (!fileName) return 'description'
        const ext = fileName.split('.').pop()?.toLowerCase()
        const icons: Record<string, string> = {
            'pdf': 'picture_as_pdf',
            'doc': 'article',
            'docx': 'article',
            'txt': 'text_snippet',
            'md': 'code',
            'html': 'html',
            'json': 'data_object',
            'csv': 'table_chart',
            'xls': 'table_chart',
            'xlsx': 'table_chart'
        }
        return icons[ext || ''] || 'description'
    }

    getScorePercent(score: number): number {
        return Math.round(score * 100)
    }

    getScoreClass(score: number): string {
        if (score >= 0.8) return 'score-high'
        if (score >= 0.5) return 'score-medium'
        return 'score-low'
    }
}
