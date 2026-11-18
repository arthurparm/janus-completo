import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Tool, ToolListResponse, ToolStats } from '../../models';
import { AdminActionsApiService } from './admin-actions-api-service';

@Injectable({ providedIn: 'root' })
export class ToolsApiService {
  constructor(private adminActions: AdminActionsApiService) {}

getTools(category?: string, permissionLevel?: string, tags?: string): Observable<ToolListResponse> {
    return this.adminActions.execute<ToolListResponse>('list_tools_api_v1_tools__get', {
      queryParams: {
        ...(category ? { category } : {}),
        ...(permissionLevel ? { permission_level: permissionLevel } : {}),
        ...(tags ? { tags } : {}),
      },
    })
  }

getToolDetails(toolName: string): Observable<Tool> {
    return this.adminActions.execute<Tool>('get_tool_details_api_v1_tools__tool_name__get', { pathParams: { tool_name: toolName } })
  }

getToolStats(): Observable<ToolStats> {
    return this.adminActions.execute<ToolStats>('get_tool_statistics_api_v1_tools_stats_usage_get')
  }

getToolCategories(): Observable<{ categories: string[] }> {
    return this.adminActions.execute<{ categories: string[] }>('list_categories_api_v1_tools_categories_list_get')
  }

getToolPermissions(): Observable<{ permission_levels: string[] }> {
    return this.adminActions.execute<{ permission_levels: string[] }>('list_permissions_api_v1_tools_permissions_list_get')
  }
}
