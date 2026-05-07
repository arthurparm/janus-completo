import { Injectable } from '@angular/core';
import { Observable, BehaviorSubject, Subject } from 'rxjs';
import { ApiContextService } from '../api-context.service';
import { JanusStatic, JanusSession, JanusPluginHandle } from '../../core/types';
declare const Janus: JanusStatic;

@Injectable({ providedIn: 'root' })
export class WebRTCApiService {
  constructor(
    private apiContext: ApiContextService
  ) {}

private _webrtcInitialized$ = new BehaviorSubject<{ status: string; error?: string } | null>(null)

private _janus?: JanusSession

private _pluginHandle?: JanusPluginHandle

private _serverUrl?: string

private _localStream$ = new BehaviorSubject<MediaStream | null>(null)

private _remoteStream$ = new BehaviorSubject<MediaStream | null>(null)

private _connectionState$ = new BehaviorSubject<string>('idle')

private _webrtcError$ = new Subject<string>()

webrtcInitialized$(): Observable<{ status: string; error?: string } | null> { return this._webrtcInitialized$.asObservable() }

localStream$(): Observable<MediaStream | null> { return this._localStream$.asObservable() }

remoteStream$(): Observable<MediaStream | null> { return this._remoteStream$.asObservable() }

connectionState$(): Observable<string> { return this._connectionState$.asObservable() }

webrtcErrors$(): Observable<string> { return this._webrtcError$.asObservable() }

initJanus(opts: { serverUrl: string; debug?: boolean }): Observable<{ status: string; error?: string }> {
    this._serverUrl = opts.serverUrl
    const out$ = new BehaviorSubject<{ status: string; error?: string }>({ status: 'initializing' })
    try {
      if (typeof Janus === 'undefined') {
        const err = 'JanusJS indisponível'
        this._webrtcInitialized$.next({ status: 'unavailable', error: err })
        out$.next({ status: 'unavailable', error: err })
        return out$.asObservable()
      }
      Janus.init({
        debug: !!opts.debug, callback: () => {
          out$.next({ status: 'initialized' })
          this._webrtcInitialized$.next({ status: 'initialized' })
          try {
            this._janus = new Janus({
              server: this._serverUrl || '',
              success: () => { this._connectionState$.next('session_ready') },
              error: (e: unknown) => { const msg = String(e); this._webrtcError$.next(msg); this._connectionState$.next('session_error'); },
              destroyed: () => { this._connectionState$.next('session_destroyed') }
            })
          } catch (e) {
            const msg = String(e)
            this._webrtcError$.next(msg)
            this._connectionState$.next('session_error')
          }
        }
      })
    } catch (e) {
      const msg = String(e)
      this._webrtcInitialized$.next({ status: 'failed', error: msg })
      out$.next({ status: 'failed', error: msg })
    }
    return out$.asObservable()
  }

attachPlugin(plugin: 'videoroom' | 'videocall', opaqueId?: string): Observable<{ status: string; error?: string }> {
    const out$ = new BehaviorSubject<{ status: string; error?: string }>({ status: 'attaching' })
    if (!this._janus) { out$.next({ status: 'failed', error: 'JanusSession ausente' }); return out$.asObservable() }
    try {
      const pluginName = plugin === 'videocall' ? 'janus.plugin.videocall' : 'janus.plugin.videoroom'
      this._janus.attach({
        plugin: pluginName,
        opaqueId,
        success: (handle: JanusPluginHandle) => {
          this._pluginHandle = handle
          out$.next({ status: 'attached' })
          this._connectionState$.next('attached')
        },
        error: (cause: unknown) => {
          const msg = String(cause)
          this._webrtcError$.next(msg)
          out$.next({ status: 'failed', error: msg })
          this._connectionState$.next('attach_error')
        },
        webrtcState: (on: boolean) => {
          this._connectionState$.next(on ? 'webrtc_up' : 'webrtc_down')
        },
        onlocalstream: (stream: MediaStream) => {
          this._localStream$.next(stream)
        },
        onremotestream: (stream: MediaStream) => {
          this._remoteStream$.next(stream)
        }
      })
    } catch (e) {
      const msg = String(e)
      this._webrtcError$.next(msg)
      out$.next({ status: 'failed', error: msg })
    }
    return out$.asObservable()
  }

createPeerConnection(iceServers?: RTCIceServer[]): RTCPeerConnection {
    const pc = new RTCPeerConnection({ iceServers })
    pc.oniceconnectionstatechange = () => { this._connectionState$.next(pc.iceConnectionState) }
    pc.ontrack = (ev) => {
      const [stream] = ev.streams
      if (stream) this._remoteStream$.next(stream)
    }
    return pc
  }

startLocalMedia(constraints: MediaStreamConstraints = { audio: true, video: true }): Promise<MediaStream> {
    return navigator.mediaDevices.getUserMedia(constraints)
      .then((stream) => { this._localStream$.next(stream); return stream })
      .catch((e) => { const msg = String(e); this._webrtcError$.next(msg); throw e })
  }

stopLocalMedia(): void {
    const s = this._localStream$.getValue()
    if (!s) return
    s.getTracks().forEach(t => t.stop())
    this._localStream$.next(null)
  }
}
