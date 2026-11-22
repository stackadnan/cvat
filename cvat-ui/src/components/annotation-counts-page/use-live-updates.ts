// SPDX-License-Identifier: MIT

import { useEffect, useRef, useState } from 'react';
import { getCore } from 'cvat-core-wrapper';

const core = getCore();

export type LiveStatus = 'connecting' | 'live' | 'reconnecting' | 'unavailable';

// the server closes with these when the user can't see the task, reconnecting won't help
const FINAL_CLOSE_CODES = [4403, 4404];
const MAX_RETRY_DELAY_MS = 10000;
// a burst of saves becomes one refetch
const CHANGE_DEBOUNCE_MS = 300;

function socketUrl(taskId: number): string {
    const url = new URL(`${core.config.backendAPI}/annotation-counts/${taskId}/live`, window.location.href);
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    return url.toString();
}

/**
 * Keeps a socket open for the task and calls onChange when its annotations change.
 * After a dropped connection comes back it also calls onChange, since changes made
 * while offline were never pushed.
 */
export default function useLiveUpdates(taskId: number, onChange: () => void): LiveStatus {
    const [status, setStatus] = useState<LiveStatus>('connecting');
    // the latest callback, so changing the job filter doesn't reopen the socket
    const onChangeRef = useRef(onChange);
    onChangeRef.current = onChange;

    useEffect(() => {
        let socket: WebSocket | null = null;
        let retryTimer: number | undefined;
        let changeTimer: number | undefined;
        let failedAttempts = 0;
        let stopped = false;

        const notifyChange = (): void => {
            window.clearTimeout(changeTimer);
            changeTimer = window.setTimeout(() => onChangeRef.current(), CHANGE_DEBOUNCE_MS);
        };

        const connect = (): void => {
            socket = new WebSocket(socketUrl(taskId));
            socket.onopen = () => {
                if (failedAttempts > 0) notifyChange();
                failedAttempts = 0;
                setStatus('live');
            };
            socket.onmessage = notifyChange;
            socket.onclose = (event) => {
                if (stopped) return;
                if (FINAL_CLOSE_CODES.includes(event.code)) {
                    setStatus('unavailable');
                    return;
                }
                const delay = Math.min(1000 * 2 ** failedAttempts, MAX_RETRY_DELAY_MS);
                failedAttempts += 1;
                setStatus('reconnecting');
                retryTimer = window.setTimeout(connect, delay);
            };
        };

        setStatus('connecting');
        connect();
        return () => {
            stopped = true;
            window.clearTimeout(retryTimer);
            window.clearTimeout(changeTimer);
            socket?.close();
        };
    }, [taskId]);

    return status;
}
