import '@testing-library/jest-dom/vitest';

// Mock global fetch
global.fetch = vi.fn();

// Mock EventSource for SSE tests
class MockEventSource {
  url: string;
  withCredentials: boolean;
  onopen: ((ev: Event) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;
  readyState = 0;
  private listeners: Map<string, EventListenerOrEventListenerObject[]> = new Map();

  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSED = 2;

  constructor(url: string | URL, init?: EventSourceInit) {
    this.url = url.toString();
    this.withCredentials = init?.withCredentials ?? false;
  }

  addEventListener(type: string, listener: EventListenerOrEventListenerObject) {
    const list = this.listeners.get(type) || [];
    list.push(listener);
    this.listeners.set(type, list);
  }

  removeEventListener(type: string, listener: EventListenerOrEventListenerObject) {
    const list = this.listeners.get(type) || [];
    this.listeners.set(type, list.filter(l => l !== listener));
  }

  close() {
    this.readyState = 2;
  }

  dispatchEvent(_event: Event): boolean {
    return true;
  }
}

global.EventSource = MockEventSource as unknown as typeof EventSource;
