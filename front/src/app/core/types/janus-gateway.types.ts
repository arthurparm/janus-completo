export interface JanusInitOptions {
    debug?: boolean | 'all' | string[];
    callback?: () => void;
    dependencies?: Record<string, unknown>;
}

export interface JanusOptions {
    server: string | string[];
    iceServers?: RTCIceServer[];
    ipv6?: boolean;
    withCredentials?: boolean;
    max_poll_events?: number;
    destroyOnUnload?: boolean;
    token?: string;
    apisecret?: string;
    success?: () => void;
    error?: (error: unknown) => void;
    destroyed?: () => void;
}

export interface JanusPluginMessage {
    message: Record<string, unknown>;
    jsep?: JanusJsep;
    success?: (data?: unknown) => void;
    error?: (error: unknown) => void;
    [key: string]: unknown;
}

export interface JanusJsep {
    type: string;
    sdp: string;
}

export interface JanusOfferParams {
    media?: {
        audioSend?: boolean;
        audioRecv?: boolean;
        videoSend?: boolean;
        videoRecv?: boolean;
        audio?: boolean | { deviceId: string };
        video?: boolean | { deviceId: string } | 'lowres' | 'hires' | 'stdres';
        data?: boolean;
        failIfNoAudio?: boolean;
        failIfNoVideo?: boolean;
        screenshareFrameRate?: number;
    };
    success?: (jsep: JanusJsep) => void;
    error?: (error: unknown) => void;
    customizeSdp?: (jsep: JanusJsep) => void;
}

export interface JanusAnswerParams {
    jsep: JanusJsep;
    media?: {
        audioSend?: boolean;
        audioRecv?: boolean;
        videoSend?: boolean;
        videoRecv?: boolean;
        audio?: boolean | { deviceId: string };
        video?: boolean | { deviceId: string } | 'lowres' | 'hires' | 'stdres';
        data?: boolean;
        failIfNoAudio?: boolean;
        failIfNoVideo?: boolean;
    };
    success?: (jsep: JanusJsep) => void;
    error?: (error: unknown) => void;
}

export interface JanusDataParams {
    text: string;
    success?: () => void;
    error?: (error: unknown) => void;
}

export interface JanusAttachOptions {
    plugin: string;
    opaqueId?: string;
    success?: (pluginHandle: JanusPluginHandle) => void;
    error?: (error: unknown) => void;
    consentDialog?: (on: boolean) => void;
    webrtcState?: (isConnected: boolean) => void;
    iceState?: (state: 'connected' | 'failed' | 'disconnected' | 'closed') => void;
    mediaState?: (medium: 'audio' | 'video', on: boolean) => void;
    slowLink?: (uplink: boolean, lost: number, mid: string) => void;
    onmessage?: (message: Record<string, unknown>, jsep?: JanusJsep) => void;
    onlocalstream?: (stream: MediaStream) => void;
    onremotestream?: (stream: MediaStream) => void;
    ondataopen?: (label: string) => void;
    oncleanup?: () => void;
    detached?: () => void;
}

export interface JanusPluginHandle {
    getId(): string;
    getPlugin(): string;
    send(parameters: JanusPluginMessage): void;
    createOffer(callbacks: JanusOfferParams): void;
    createAnswer(callbacks: JanusAnswerParams): void;
    handleRemoteJsep(callbacks: { jsep: JanusJsep }): void;
    dtmf(parameters: { tones: string; duration?: number; gap?: number }): void;
    data(parameters: JanusDataParams): void;
    isAudioMuted(): boolean;
    muteAudio(): void;
    unmuteAudio(): void;
    isVideoMuted(): boolean;
    muteVideo(): void;
    unmuteVideo(): void;
    getBitrate(): string;
    hangup(sendRequest?: boolean): void;
    detach(parameters?: { success?: () => void; error?: (error: unknown) => void }): void;
}

export interface JanusStatic {
    init(options: JanusInitOptions): void;
    isWebrtcSupported(): boolean;
    debug(...args: unknown[]): void;
    log(...args: unknown[]): void;
    warn(...args: unknown[]): void;
    error(...args: unknown[]): void;
    randomString(length: number): string;
    attachMediaStream(element: HTMLMediaElement, stream: MediaStream): void;
    new (options: JanusOptions): JanusSession;
}

export interface JanusSession {
    getServer(): string;
    isConnected(): boolean;
    getSessionId(): string;
    attach(options: JanusAttachOptions): void;
    destroy(parameters?: { success?: () => void; error?: (error: unknown) => void }): void;
}
