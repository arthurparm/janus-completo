import { Component, OnInit, OnDestroy, inject, ViewChild, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { UiButtonComponent } from '../../shared/components/ui/button/button.component';
import { UiIconComponent } from '../../shared/components/ui/icon/icon.component';
import { FormsModule } from '@angular/forms';
import { JanusApiService } from '../../services/janus-api.service';
import { MatTabsModule } from '@angular/material/tabs';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';

@Component({
    selector: 'app-senses',
    standalone: true,
    imports: [
        CommonModule,
        UiButtonComponent,
        UiIconComponent,
        FormsModule,
        MatTabsModule,
        MatProgressBarModule,
        MatFormFieldModule,
        MatInputModule
    ],
    templateUrl: './senses.html',
    styleUrl: './senses.scss'
})
export class SensesComponent implements OnInit, OnDestroy {
    private api = inject(JanusApiService);

    // Configuration
    janusUrl = 'wss://janus.conf.meetecho.com/ws'; // Default public echo test for demo
    isConnected = false;
    statusMessage = 'Offline';

    // Vision State
    @ViewChild('videoElement') videoElement!: ElementRef<HTMLVideoElement>;
    isDragging = false;
    uploadProgress = 0;
    analyzing = false;
    lastAnalysisResult = '';

    // Audio State
    isListening = false;
    volumeLevel = 0; // 0-100 for visualizer
    private audioInterval: any;

    ngOnInit() {
        // Check if we have a stored URL
        const stored = localStorage.getItem('janus_url');
        if (stored) this.janusUrl = stored;
    }

    ngOnDestroy() {
        this.disconnect();
        if (this.audioInterval) clearInterval(this.audioInterval);
    }

    // --- WebRTC Connection ---

    connect() {
        this.statusMessage = 'Connecting...';
        localStorage.setItem('janus_url', this.janusUrl);

        this.api.initJanus({ serverUrl: this.janusUrl, debug: true }).subscribe({
            next: (status) => {
                if (status.status === 'initialized') {
                    this.statusMessage = 'Janus Session Established';
                    this.attachVideoPlugin();
                } else if (status.status === 'failed') {
                    this.statusMessage = 'Connection Failed: ' + status.error;
                }
            }
        });
    }

    disconnect() {
        // Teardown logic mock
        this.isConnected = false;
        this.statusMessage = 'Disconnected';
    }

    attachVideoPlugin() {
        this.api.attachPlugin('videoroom').subscribe(status => {
            if (status.status === 'attached') {
                this.isConnected = true;
                this.statusMessage = 'System Online. Waiting for feed...';
                // In a real scenario, we would join a room here.
                // For now, we simulate success.
            }
        });
    }

    // --- Vision: Dropzone ---

    onDragOver(event: DragEvent) {
        event.preventDefault();
        event.stopPropagation();
        this.isDragging = true;
    }

    onDragLeave(event: DragEvent) {
        event.preventDefault();
        event.stopPropagation();
        this.isDragging = false;
    }

    onDrop(event: DragEvent) {
        event.preventDefault();
        event.stopPropagation();
        this.isDragging = false;

        const files = event.dataTransfer?.files;
        if (files && files.length > 0) {
            this.uploadImage(files[0]);
        }
    }

    onFileSelected(event: any) {
        const file = event.target.files[0];
        if (file) this.uploadImage(file);
    }

    uploadImage(file: File) {
        this.uploadProgress = 1;
        this.analyzing = true;
        this.lastAnalysisResult = '';

        this.api.uploadDocument(file).subscribe({
            next: (event) => {
                if (event.progress) {
                    this.uploadProgress = event.progress;
                }
                if (event.response) {
                    this.uploadProgress = 100;
                    this.analyzeImage(event.response.doc_id);
                }
            },
            error: (err) => {
                this.analyzing = false;
                this.statusMessage = 'Upload Failed';
            }
        });
    }

    analyzeImage(docId: string) {
        // Simulate "Agent Thinking" about the image
        // In a real implementation this would call `chat.sendMessage` with the doc context
        setTimeout(() => {
            this.analyzing = false;
            this.lastAnalysisResult = `Analysis Complete for DOC-${docId.substring(0, 6)}: Image contains technical diagram of a neural network architecture. High confidence (98%).`;
        }, 2000);
    }

    // --- Audio ---

    toggleMic() {
        this.isListening = !this.isListening;
        if (this.isListening) {
            // Mock audio visualizer
            this.audioInterval = setInterval(() => {
                this.volumeLevel = Math.random() * 100;
            }, 100);
        } else {
            clearInterval(this.audioInterval);
            this.volumeLevel = 0;
        }
    }
}
