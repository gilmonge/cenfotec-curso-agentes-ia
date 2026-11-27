import { afterEach, describe, expect, it, vi } from 'vitest';
import { getWorkflow, resumeWorkflow, startWorkflow, WorkflowApiError } from '../workflowApi.js';

afterEach(() => vi.unstubAllGlobals());

describe('workflowApi', () => {
  it('starts pre_grooming through the same-origin API without writing browser storage', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ workflow_id: 'wf-1' }), { status: 201 }));
    vi.stubGlobal('fetch', fetchMock);
    const before = Object.keys(localStorage);
    const body = { mode: 'pre_grooming', requirement: 'Requisito de prueba' };

    await expect(startWorkflow(body)).resolves.toEqual({ workflow_id: 'wf-1' });
    expect(fetchMock).toHaveBeenCalledWith('/api/workflows', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify(body),
      credentials: 'same-origin',
      cache: 'no-store',
    }));
    expect(Object.keys(localStorage)).toEqual(before);
  });

  it('gets a workflow and resumes with its interrupt_id in the request body', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ workflow_id: 'wf/1' }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ status: 'interrupted' }), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);
    const controller = new AbortController();
    const body = { kind: 'business_answers', interrupt_id: 'interrupt-1', response: { answers: [] } };

    await getWorkflow('wf/1', { signal: controller.signal });
    await resumeWorkflow('wf/1', body, { signal: controller.signal });

    expect(fetchMock.mock.calls[0][0]).toBe('/api/workflows/wf%2F1');
    expect(fetchMock.mock.calls[0][1].signal).toBe(controller.signal);
    expect(fetchMock.mock.calls[1][0]).toBe('/api/workflows/wf%2F1/resume');
    expect(fetchMock.mock.calls[1][1]).toMatchObject({ method: 'POST', body: JSON.stringify(body) });
  });

  it.each([400, 404, 409, 422, 503, 504])('reports a safe, actionable message for HTTP %s', async (status) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({
      error: { code: 'PUBLIC_ERROR', message: 'internal-looking raw error', retryable: status >= 500 },
    }), { status })));

    await expect(getWorkflow('wf-1')).rejects.toMatchObject({
      name: 'WorkflowApiError', status, retryable: status >= 500,
    });
    await expect(getWorkflow('wf-1')).rejects.not.toHaveProperty('message', 'internal-looking raw error');
    expect(WorkflowApiError).toBeDefined();
  });

  it('explains that a missing workflow must be restarted', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({
      error: { code: 'WORKFLOW_NOT_FOUND', message: 'Not found', retryable: false },
    }), { status: 404 })));

    await expect(getWorkflow('lost-workflow')).rejects.toThrow(/no se encontró el flujo.*inicie uno nuevo/i);
  });

  it('does not turn an intentional cancellation into a network failure', async () => {
    const abort = new DOMException('Aborted', 'AbortError');
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(abort));
    await expect(getWorkflow('wf-1')).rejects.toBe(abort);
  });
});
