import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { fetchWithRetry } from './fetch-retry';

describe('fetchWithRetry', () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it('should return a successful response on the first attempt', async () => {
        const mockResponse = new Response('Success', { status: 200 });
        const fetchSpy = vi.spyOn(global, 'fetch').mockResolvedValue(mockResponse);

        const response = await fetchWithRetry('https://example.com');

        expect(response.status).toBe(200);
        expect(await response.text()).toBe('Success');
        expect(fetchSpy).toHaveBeenCalledTimes(1);
    });

    it('should retry on failure and eventually succeed', async () => {
        const mockErrorResponse = new Response('Error', { status: 500 });
        const mockSuccessResponse = new Response('Success', { status: 200 });

        const fetchSpy = vi.spyOn(global, 'fetch')
            .mockResolvedValueOnce(mockErrorResponse)
            .mockResolvedValueOnce(mockErrorResponse)
            .mockResolvedValueOnce(mockSuccessResponse);

        const promise = fetchWithRetry('https://example.com', undefined, { maxRetries: 4, backoffMs: 100 });

        // Allow microtasks to run for the first fetch
        await vi.advanceTimersByTimeAsync(0);

        // First retry after 100ms
        await vi.advanceTimersByTimeAsync(100);

        // Second retry after 200ms
        await vi.advanceTimersByTimeAsync(200);

        const response = await promise;

        expect(response.status).toBe(200);
        expect(await response.text()).toBe('Success');
        expect(fetchSpy).toHaveBeenCalledTimes(3);
    });

    it('should throw an error after all retries fail', async () => {
        const mockErrorResponse = new Response('Error', { status: 500 });
        const fetchSpy = vi.spyOn(global, 'fetch').mockResolvedValue(mockErrorResponse);

        const promise = fetchWithRetry('https://example.com', undefined, { maxRetries: 3, backoffMs: 100 });

        const rejectionPromise = expect(promise).rejects.toThrow('HTTP 500');
        await vi.runAllTimersAsync();
        await rejectionPromise;

        expect(fetchSpy).toHaveBeenCalledTimes(3);
    });

    it('should handle network errors and throw after all retries', async () => {
        const fetchSpy = vi.spyOn(global, 'fetch').mockRejectedValue(new Error('Network error'));

        const promise = fetchWithRetry('https://example.com', undefined, { maxRetries: 3, backoffMs: 100 });

        const rejectionPromise = expect(promise).rejects.toThrow('Network error');
        await vi.runAllTimersAsync();
        await rejectionPromise;

        expect(fetchSpy).toHaveBeenCalledTimes(3);
    });
});
