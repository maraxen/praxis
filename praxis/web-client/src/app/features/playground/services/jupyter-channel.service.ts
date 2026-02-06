import { Injectable, OnDestroy } from '@angular/core';
import { Subject, Observable } from 'rxjs';
import { filter, map } from 'rxjs/operators';

export interface JupyterMessage {
  type: string;
  [key: string]: any;
}

@Injectable({
  providedIn: 'root'
})
export class JupyterChannelService implements OnDestroy {
  private channel: BroadcastChannel;
  private messageSubject = new Subject<JupyterMessage>();

  // Observable for all messages
  public messages$: Observable<JupyterMessage> = this.messageSubject.asObservable();

  // Observable specifically for 'praxis:ready' signal
  public onReady$: Observable<JupyterMessage> = this.messages$.pipe(
    filter(msg => msg.type === 'praxis:ready')
  );

  constructor() {
    const channelName = 'praxis_repl';

    this.channel = new BroadcastChannel(channelName);
    this.channel.onmessage = (event) => {
      this.messageSubject.next(event.data as JupyterMessage);
    };
  }

  /**
   * Send a message to the JupyterLite kernel.
   * @param message The message object to send.
   */
  sendMessage(message: JupyterMessage) {
    this.channel.postMessage(message);
  }

  ngOnDestroy() {
    this.channel.close();
    this.messageSubject.complete();
  }
}
