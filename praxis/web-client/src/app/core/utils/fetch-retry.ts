export async function fetchWithRetry(
    url: string,
    options?: RequestInit,
    config?: { maxRetries?: number; backoffMs?: number }
): Promise<Response> {
    const maxRetries = config?.maxRetries ?? 3;
    const backoffMs = config?.backoffMs ?? 1000;

    let lastError: Error | null = null;

    for (let attempt = 0; attempt < maxRetries; attempt++) {
        try {
            const response = await fetch(url, options);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return response;
        } catch (error) {
            lastError = error as Error;
            console.warn(`Fetch attempt ${attempt + 1}/${maxRetries} failed for ${url}:`, error);

            if (attempt < maxRetries - 1) {
                await new Promise(r => setTimeout(r, backoffMs * (attempt + 1)));
            }
        }
    }

    throw lastError ?? new Error(`Failed to fetch ${url} after ${maxRetries} attempts`);
}
