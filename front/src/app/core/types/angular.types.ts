/**
 * Tipos TypeScript estritos para melhores práticas Angular
 * Este arquivo contém interfaces e tipos reutilizáveis em todo o projeto
 */

// Tipos base para componentes
export type ComponentSize = 'small' | 'medium' | 'large';
export type ComponentColor = 'primary' | 'accent' | 'warn' | 'success' | 'info';
export type ThemeMode = 'light' | 'dark' | 'auto';

// Tipos para formulários
export interface FormFieldConfig {
  name: string;
  label: string;
  type: 'text' | 'email' | 'password' | 'number' | 'tel' | 'url' | 'textarea' | 'select' | 'checkbox' | 'radio' | 'date' | 'datetime-local';
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
  readonly?: boolean;
  min?: number;
  max?: number;
  minLength?: number;
  maxLength?: number;
  pattern?: string;
  options?: Array<{value: string | number | boolean; label: string; disabled?: boolean}>;
  validationMessages?: Record<string, string>;
  asyncValidators?: string[];
}

export interface FormConfig {
  fields: FormFieldConfig[];
  submitButtonText?: string;
  cancelButtonText?: string;
  showCancelButton?: boolean;
  validateOnSubmit?: boolean;
  validateOnBlur?: boolean;
  validateOnChange?: boolean;
}

// Tipos para notificações
export interface NotificationConfig {
  id?: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title?: string;
  message: string;
  duration?: number;
  persistent?: boolean;
  actions?: NotificationAction[];
  position?: 'top-left' | 'top-center' | 'top-right' | 'bottom-left' | 'bottom-center' | 'bottom-right';
  showCloseButton?: boolean;
  icon?: string;
}

export interface NotificationAction {
  label: string;
  action: () => void;
  type?: 'primary' | 'secondary' | 'danger';
}

// Tipos para modais e diálogos
export interface ModalConfig {
  title?: string;
  message?: string;
  size?: ComponentSize;
  showCloseButton?: boolean;
  backdrop?: boolean | 'static';
  keyboard?: boolean;
  centered?: boolean;
  scrollable?: boolean;
  fullscreen?: boolean;
}

export interface ConfirmDialogConfig extends ModalConfig {
  confirmButtonText?: string;
  cancelButtonText?: string;
  confirmButtonType?: ComponentColor;
  icon?: string;
  dangerMode?: boolean;
}

// Tipos para loading e estados
export interface LoadingState {
  isLoading: boolean;
  message?: string;
  subMessage?: string;
  progress?: number;
  showProgress?: boolean;
  cancellable?: boolean;
}

export interface ErrorState {
  hasError: boolean;
  message?: string;
  title?: string;
  code?: string | number;
  details?: unknown;
  retryable?: boolean;
  actions?: ErrorAction[];
}

export interface ErrorAction {
  label: string;
  action: () => void;
  type?: 'primary' | 'secondary' | 'danger';
  icon?: string;
}

// Tipos para paginação
export interface PaginationConfig {
  page: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
  hasNext: boolean;
  hasPrevious: boolean;
  showSizeOptions?: boolean;
  sizeOptions?: number[];
  showInfo?: boolean;
}

export interface PaginationState extends PaginationConfig {
  loading?: boolean;
  error?: string;
}

// Tipos para ordenação
export interface SortConfig {
  field: string;
  direction: 'asc' | 'desc';
  multi?: boolean;
}

// Tipos para filtros
export interface FilterConfig {
  field: string;
  operator: 'equals' | 'contains' | 'startsWith' | 'endsWith' | 'greaterThan' | 'lessThan' | 'between' | 'in';
  value: any;
  label?: string;
  type?: 'text' | 'number' | 'date' | 'select' | 'multiselect';
  options?: Array<{value: any; label: string}>;
}

// Tipos para APIs e serviços
export interface ApiResponse<T = any> {
  data: T;
  success: boolean;
  message?: string;
  errors?: string[];
  timestamp: string;
  requestId?: string;
}

export interface ApiError {
  message: string;
  code?: string;
  details?: any;
  timestamp: string;
  requestId?: string;
  statusCode?: number;
}

export interface ApiRequestConfig {
  timeout?: number;
  retries?: number;
  retryDelay?: number;
  cache?: boolean | number;
  headers?: Record<string, string>;
  params?: Record<string, any>;
}

// Tipos para autenticação
export interface AuthUser {
  id: string;
  email: string;
  name: string;
  avatar?: string;
  roles: string[];
  permissions: string[];
  metadata?: Record<string, any>;
}

export interface AuthState {
  isAuthenticated: boolean;
  user: AuthUser | null;
  token: string | null;
  refreshToken: string | null;
  expiresAt: number | null;
}

// Tipos para temas e estilos
export interface ThemeConfig {
  mode: ThemeMode;
  primaryColor: string;
  accentColor: string;
  backgroundColor: string;
  textColor: string;
  borderRadius: ComponentSize;
  fontSize: ComponentSize;
}

// Tipos para analytics e métricas
export interface MetricData {
  timestamp: number;
  value: number;
  label?: string;
  metadata?: Record<string, any>;
}

export interface ChartData {
  labels: string[];
  datasets: ChartDataset[];
}

export interface ChartDataset {
  label: string;
  data: number[];
  backgroundColor?: string | string[];
  borderColor?: string | string[];
  borderWidth?: number;
  fill?: boolean;
  tension?: number;
}

// Tipos para componentes de formulário avançados
export interface SelectOption {
  value: any;
  label: string;
  disabled?: boolean;
  description?: string;
  icon?: string;
  group?: string;
}

export interface AutoCompleteConfig {
  minLength?: number;
  debounceTime?: number;
  placeholder?: string;
  multiple?: boolean;
  showClear?: boolean;
  forceSelection?: boolean;
  emptyMessage?: string;
}

// Tipos para drag and drop
export interface DragDropConfig {
  disabled?: boolean;
  dragHandle?: string;
  dropZone?: string;
  dragPreview?: 'clone' | 'native';
  dragData?: any;
}

// Tipos para componentes de layout
export interface LayoutConfig {
  header?: boolean;
  sidebar?: boolean;
  footer?: boolean;
  breadcrumbs?: boolean;
  themeToggle?: boolean;
  responsive?: boolean;
}

// Tipos para componentes de navegação
export interface NavigationItem {
  id: string;
  label: string;
  icon?: string;
  route?: string;
  external?: boolean;
  children?: NavigationItem[];
  permissions?: string[];
  roles?: string[];
  badge?: string | number;
  badgeColor?: ComponentColor;
  active?: boolean;
  disabled?: boolean;
  separator?: boolean;
}

// Tipos para componentes de tabela
export interface TableColumn {
  field: string;
  header: string;
  type?: 'text' | 'number' | 'date' | 'boolean' | 'currency' | 'percent' | 'badge' | 'actions';
  sortable?: boolean;
  filterable?: boolean;
  width?: string;
  align?: 'left' | 'center' | 'right';
  formatter?: (value: any, row: any) => string;
  template?: string;
  sticky?: boolean;
  hidden?: boolean;
}

export interface TableConfig {
  columns: TableColumn[];
  paginated?: boolean;
  sortable?: boolean;
  filterable?: boolean;
  selectable?: boolean;
  expandable?: boolean;
  actions?: TableAction[];
  emptyMessage?: string;
  loading?: boolean;
}

export interface TableAction {
  label: string;
  icon?: string;
  action: (row: any) => void;
  type?: ComponentColor;
  disabled?: (row: any) => boolean;
  visible?: (row: any) => boolean;
}

// Tipos para componentes de upload
export interface UploadConfig {
  multiple?: boolean;
  accept?: string;
  maxFileSize?: number;
  maxFiles?: number;
  showUploadList?: boolean;
  showPreview?: boolean;
  directory?: boolean;
  drag?: boolean;
  disabled?: boolean;
}

export interface UploadFile {
  uid: string;
  name: string;
  size: number;
  type: string;
  originFileObj?: File;
  percent?: number;
  status?: 'uploading' | 'success' | 'error' | 'removed';
  response?: any;
  error?: any;
}

// Tipos para componentes de chat
export interface ChatMessage {
  id?: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: Date;
  metadata?: Record<string, any>;
  attachments?: ChatAttachment[];
  citations?: ChatCitation[];
}

export interface ChatAttachment {
  id: string;
  name: string;
  type: string;
  size: number;
  url?: string;
  metadata?: Record<string, any>;
}

export interface ChatCitation {
  id: string;
  title: string;
  content: string;
  source: string;
  page?: number;
  metadata?: Record<string, any>;
}

// Tipos para componentes de voz
export interface VoiceConfig {
  language?: string;
  continuous?: boolean;
  interimResults?: boolean;
  maxAlternatives?: number;
  grammars?: any; // SpeechGrammarList - tipo não disponível em todos os navegadores
}

// Tipos para componentes de notificação em tempo real
export interface RealTimeNotification {
  id: string;
  type: 'info' | 'warning' | 'error' | 'success';
  title: string;
  message: string;
  timestamp: Date;
  read: boolean;
  persistent?: boolean;
  actions?: NotificationAction[];
  metadata?: Record<string, any>;
}

// Tipos para componentes de dashboard
export interface DashboardWidget {
  id: string;
  type: 'metric' | 'chart' | 'table' | 'list' | 'card';
  title: string;
  size?: 'small' | 'medium' | 'large' | 'full';
  data?: any;
  config?: any;
  refreshInterval?: number;
  permissions?: string[];
}

// Tipos para componentes de configuração
export interface SettingsSection {
  id: string;
  title: string;
  description?: string;
  icon?: string;
  items: SettingsItem[];
}

export interface SettingsItem {
  id: string;
  label: string;
  type: 'text' | 'number' | 'boolean' | 'select' | 'multiselect' | 'color' | 'file';
  value: any;
  description?: string;
  options?: SelectOption[];
  validation?: any;
  disabled?: boolean;
  dependsOn?: string;
}

// Utility types
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

export type Nullable<T> = T | null;

export type Optional<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;

export type RequiredKeys<T> = {
  [K in keyof T]-?: {} extends Pick<T, K> ? never : K;
}[keyof T];

export type OptionalKeys<T> = {
  [K in keyof T]-?: {} extends Pick<T, K> ? K : never;
}[keyof T];

// Tipos para estados de loading
export interface LoadingState {
  isLoading: boolean
  message?: string
  progress?: number
  timestamp: number
  completedAt?: number
  global?: boolean
  http?: boolean
}

export interface LoadingConfig {
  message?: string
  progress?: number
  global?: boolean
  http?: boolean
}

export interface LoadingOptions {
  showSpinner?: boolean
  showMessage?: boolean
  overlay?: boolean
  delay?: number
  minDuration?: number
}