import { Injectable, inject, signal } from '@angular/core';
import { Observable, Subject, map, filter } from 'rxjs';
import { webSocket, WebSocketSubject } from 'rxjs/webSocket';
import { environment } from '@env/environment';
import { ReplOutput, ReplRuntime, CompletionItem, SignatureInfo, ReplacementVariable } from './repl-runtime.interface';
import { toObservable } from '@angular/core/rxjs-interop';
import { ReplService } from '../api-generated/services/ReplService';
import { ApiWrapperService } from './api-wrapper.service';

interface ReplMessage {
    type: string;
    id?: string;
    payload?: any;
}

interface ReplVarsUpdateMessage extends ReplMessage {
    type: 'VARS_UPDATE';
    payload: {
        variables: ReplacementVariable[];
    };
}

interface ReplResultMessage extends ReplMessage {
    type: 'RESULT';
    id: string;
    payload: {
        output: string;
        more: boolean;
    };
}

interface ReplErrorMessage extends ReplMessage {
    type: 'ERROR';
    id: string;
    payload: {
        error: string;
    };
}

interface ReplCompletionMessage extends ReplMessage {
    type: 'COMPLETION_RESULT';
    id: string;
    payload: {
        matches: Array<string | CompletionItem>;
    };
}

interface ReplSignatureMessage extends ReplMessage {
    type: 'SIGNATURE_RESULT';
    id: string;
    payload: {
        signatures: SignatureInfo[];
    };
}

@Injectable({
    providedIn: 'root'
})
export class PlaygroundRuntimeService implements ReplRuntime {
    private readonly WS_URL = `${environment.wsUrl}/repl/session`;
    private readonly apiWrapper = inject(ApiWrapperService);
    private socket$: WebSocketSubject<unknown> | null = null;
    private connectionSubject = new Subject<void>();

    /** Signal for runtime variables */
    readonly variables = signal<ReplacementVariable[]>([]);

    /** Observable for RxJS interop */
    readonly variables$ = toObservable(this.variables);

    connect(): Observable<void> {
        if (this.socket$) {
            return this.connectionSubject.asObservable();
        }

        this.socket$ = webSocket({
            url: this.WS_URL,
            openObserver: {
                next: () => {
                    console.log('REPL WebSocket connected');
                    this.connectionSubject.next();
                }
            }
        });

        // Listen for global updates (like variables) on the main socket observable
        // Note: Creating a subscription here might consume messages intended for execute()
        // if execute() uses multiplexing. However, webSocket subject multicasts.
        this.socket$.subscribe(msg => {
            const m = msg as ReplMessage;
            if (m.type === 'VARS_UPDATE') {
                const update = m as ReplVarsUpdateMessage;
                this.variables.set(update.payload.variables);
            }
        });

        return this.connectionSubject.asObservable();
    }

    disconnect(): void {
        if (this.socket$) {
            this.socket$.complete();
            this.socket$ = null;
        }
    }

    execute(code: string): Observable<ReplOutput> {
        if (!this.socket$) {
            throw new Error('REPL not connected');
        }

        const commandId = crypto.randomUUID();
        this.socket$.next({
            type: 'EXEC',
            id: commandId,
            payload: { code }
        });

        return this.socket$.asObservable().pipe(
            filter(msg => (msg as ReplMessage).id === commandId),
            map(msg => {
                const m = msg as ReplMessage;
                if (m.type === 'RESULT') {
                    const res = m as ReplResultMessage;
                    return {
                        type: 'result' as const,
                        content: res.payload.output,
                        more: res.payload.more // backend push() returns more
                    };
                } else if (m.type === 'ERROR') {
                    const err = m as ReplErrorMessage;
                    return {
                        type: 'error' as const,
                        content: err.payload.error
                    };
                }
                return { type: 'error' as const, content: 'Unknown response' };
            })
        );
    }

    restart(): Observable<void> {
        if (!this.socket$) return new Observable();

        const id = crypto.randomUUID();
        this.socket$.next({ type: 'RESTART', id });

        return this.socket$.asObservable().pipe(
            filter(msg => (msg as ReplMessage).id === id),
            map(() => void 0)
        );
    }

    saveSession(history: string[]) {
        return this.apiWrapper.wrap(ReplService.saveSessionApiV1ReplSaveSessionPost({ history }));
    }

    interrupt(): void {
        // Backend console.push is synchronous for now, interrupt is hard without signals
        // but we can send a message if we had an async kernel
        this.socket$?.next({ type: 'INTERRUPT' });
    }

    async getCompletions(code: string, _cursor: number): Promise<CompletionItem[]> {
        if (!this.socket$) return [];

        const id = crypto.randomUUID();
        return new Promise((resolve) => {
            const subscription = this.socket$?.asObservable().subscribe(msg => {
                const m = msg as ReplMessage;
                if (m.id === id && m.type === 'COMPLETION_RESULT') {
                    subscription?.unsubscribe();
                    const completion = m as ReplCompletionMessage;
                    // Backend may return either string[] or CompletionItem[]
                    const matches = completion.payload.matches || [];
                    const items = matches.map((item: string | CompletionItem) =>
                        typeof item === 'string' ? { name: item, type: 'unknown' } : item
                    );
                    resolve(items);
                }
            });

            this.socket$?.next({
                type: 'COMPLETION',
                id,
                payload: { code }
            });

            // Timeout after 2 seconds
            setTimeout(() => {
                subscription?.unsubscribe();
                resolve([]);
            }, 2000);
        });
    }

    async getSignatures(code: string, _cursor: number): Promise<SignatureInfo[]> {
        if (!this.socket$) return [];

        const id = crypto.randomUUID();
        return new Promise((resolve) => {
            const subscription = this.socket$?.asObservable().subscribe(msg => {
                const m = msg as ReplMessage;
                if (m.id === id && m.type === 'SIGNATURE_RESULT') {
                    subscription?.unsubscribe();
                    const sig = m as ReplSignatureMessage;
                    resolve(sig.payload.signatures || []);
                }
            });

            this.socket$?.next({
                type: 'SIGNATURES',
                id,
                payload: { code }
            });

            // Timeout after 2 seconds
            setTimeout(() => {
                subscription?.unsubscribe();
                resolve([]);
            }, 2000);
        });
    }
}
