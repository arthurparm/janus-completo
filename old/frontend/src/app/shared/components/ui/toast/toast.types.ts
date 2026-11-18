export type ToastType = 'default' | 'success' | 'error' | 'warning' | 'info' | 'destructive';

export interface ToastConfig {
    message: string;
    type?: ToastType;
    duration?: number;
    action?: string;
    actionCallback?: () => void;
}

export interface ToastData extends ToastConfig {
    id: number;
}
