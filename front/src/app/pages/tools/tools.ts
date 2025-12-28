import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core'
import { CommonModule } from '@angular/common'
import { FormsModule } from '@angular/forms'
import { JanusApiService } from '../../services/janus-api.service'
import { DemoService } from '../../core/services/demo.service'
import { MatIconModule } from '@angular/material/icon'

export interface Tool {
    name: string
    description: string
    category: string
    permission_level: string
    rate_limit_per_minute?: number
    requires_confirmation: boolean
    tags: string[]
}

export interface ToolStats {
    total_tools_registered: number
    total_calls: number
    successful_calls: number
    success_rate: number
    tool_usage: Record<string, { calls: number; success_rate: number }>
}

@Component({
    selector: 'app-tools',
    standalone: true,
    imports: [CommonModule, FormsModule, MatIconModule],
    templateUrl: './tools.html',
    styleUrl: './tools.scss'
})
export class ToolsComponent implements OnInit {
    private api = inject(JanusApiService)
    private cdr = inject(ChangeDetectorRef)
    private demoService = inject(DemoService)

    tools: Tool[] = []
    filteredTools: Tool[] = []
    stats: ToolStats | null = null
    categories: string[] = []
    permissionLevels: string[] = []

    loading = true
    error: string | null = null

    // Filters
    searchQuery = ''
    categoryFilter = ''
    permissionFilter = ''
    selectedTool: Tool | null = null

    get isOffline() {
        return this.demoService.isOffline()
    }

    ngOnInit() {
        this.loadData()
    }

    loadData() {
        this.loading = true
        this.error = null

        if (this.demoService.isOffline()) {
            this.loading = false
            this.tools = []
            this.filteredTools = []
            return
        }

        // Load tools
        this.api.getTools().subscribe({
            next: (response: any) => {
                this.tools = response.tools || []
                this.applyFilters()
                this.loading = false
                this.cdr.detectChanges()
            },
            error: (err: any) => {
                console.error('Error loading tools:', err)
                if (err.status === 0 || err.status === 504) {
                    this.demoService.enableOfflineMode();
                    this.loading = false
                    this.tools = []
                    this.filteredTools = []
                } else {
                    this.error = 'Falha ao carregar ferramentas'
                    this.loading = false
                }
                this.cdr.detectChanges()
            }
        })

        // Load stats
        this.api.getToolStats().subscribe({
            next: (stats: any) => {
                this.stats = stats
                this.cdr.detectChanges()
            },
            error: () => { } // Stats are optional
        })

        // Load categories
        this.api.getToolCategories().subscribe({
            next: (response: any) => {
                this.categories = response.categories || []
                this.cdr.detectChanges()
            },
            error: () => { }
        })

        // Load permission levels
        this.api.getToolPermissions().subscribe({
            next: (response: any) => {
                this.permissionLevels = response.permission_levels || []
                this.cdr.detectChanges()
            },
            error: () => { }
        })
    }

    applyFilters() {
        let result = [...this.tools]

        // Search filter
        if (this.searchQuery.trim()) {
            const query = this.searchQuery.toLowerCase()
            result = result.filter(t =>
                t.name.toLowerCase().includes(query) ||
                t.description.toLowerCase().includes(query) ||
                t.tags.some(tag => tag.toLowerCase().includes(query))
            )
        }

        // Category filter
        if (this.categoryFilter) {
            result = result.filter(t => t.category === this.categoryFilter)
        }

        // Permission filter
        if (this.permissionFilter) {
            result = result.filter(t => t.permission_level === this.permissionFilter)
        }

        this.filteredTools = result
    }

    selectTool(tool: Tool) {
        this.selectedTool = this.selectedTool?.name === tool.name ? null : tool
    }

    getCategoryIcon(category: string): string {
        const icons: Record<string, string> = {
            'productivity': 'work',
            'search': 'search',
            'code': 'code',
            'data': 'storage',
            'communication': 'chat',
            'utility': 'build',
            'api': 'api',
            'custom': 'extension',
            'system': 'settings',
            'llm': 'psychology'
        }
        return icons[category.toLowerCase()] || 'extension'
    }

    getPermissionColor(level: string): string {
        const colors: Record<string, string> = {
            'safe': 'permission-safe',
            'moderate': 'permission-moderate',
            'dangerous': 'permission-dangerous',
            'critical': 'permission-critical'
        }
        return colors[level.toLowerCase()] || 'permission-safe'
    }

    getPermissionIcon(level: string): string {
        const icons: Record<string, string> = {
            'safe': 'check_circle',
            'moderate': 'warning',
            'dangerous': 'error',
            'critical': 'dangerous'
        }
        return icons[level.toLowerCase()] || 'help'
    }

    formatRateLimit(limit?: number): string {
        if (!limit) return 'Sem limite'
        return `${limit}/min`
    }

    getStatsByCategory() {
        const categoryStats: Record<string, number> = {}
        this.tools.forEach(tool => {
            categoryStats[tool.category] = (categoryStats[tool.category] || 0) + 1
        })
        return categoryStats
    }
}
