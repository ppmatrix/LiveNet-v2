import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { failure, json, mockHttp, page, resource, user } from '../test/http';
import type { Handler } from '../test/http';
import { renderApp } from '../test/renderApp';

function inventoryHttp(handler: Handler) {
  return mockHttp((url, options) => {
    if (url.pathname.endsWith('/auth/me')) return json({ user });
    if (url.pathname.endsWith('/auth/csrf')) return json({ csrf_token: 'test-session-csrf' });
    return handler(url, options);
  });
}

describe('inventário e detalhe', () => {
  it('mostra os campos reais e navega da lista para o detalhe', async () => {
    mockHttp();
    renderApp();
    const link = await screen.findByRole('link', { name: /Router do laboratório/ });
    expect(screen.getByRole('columnheader', { name: 'Estado administrativo' })).toBeInTheDocument();
    expect(screen.getByText(resource.id)).toBeInTheDocument();
    expect(screen.getByRole('cell', { name: 'Ativo' })).toBeInTheDocument();
    await userEvent.click(link);
    await screen.findByRole('heading', { name: resource.display_name });
    expect(screen.getByText(resource.description!)).toBeInTheDocument();
    expect(screen.getByText('Sem atributos adicionais.')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '← Voltar ao inventário' })).toHaveAttribute('href', '/inventory');
  });

  it('pagina com page/per_page e respeita a página devolvida', async () => {
    const fetchMock = inventoryHttp(url => json(page([resource], {
      total: 51, page: Number(url.searchParams.get('page')), per_page: 50,
    })));
    renderApp();
    await screen.findByRole('link', { name: /Router do laboratório/ });
    expect(screen.getByRole('button', { name: 'Anterior' })).toBeDisabled();
    await userEvent.click(screen.getByRole('button', { name: 'Seguinte' }));
    await waitFor(() => expect(screen.getByRole('button', { name: 'Seguinte' })).toBeDisabled());
    expect(screen.getByRole('button', { name: 'Anterior' })).toBeEnabled();
    const last = fetchMock.mock.calls.at(-1)!;
    expect(new URL(String(last[0])).searchParams.get('page')).toBe('2');
    expect(new URL(String(last[0])).searchParams.get('per_page')).toBe('50');
  });

  it('envia apenas os filtros aprovados e reinicia a página ao filtrar', async () => {
    const fetchMock = inventoryHttp(url => json(page([resource], {
      page: Number(url.searchParams.get('page')), total: 101,
    })));
    renderApp('/inventory?page=2&per_page=50');
    await screen.findByRole('link', { name: /Router do laboratório/ });
    await userEvent.selectOptions(screen.getByLabelText('Tipo de recurso'), 'network_device');
    await waitFor(() => expect(new URL(String(fetchMock.mock.calls.at(-1)![0])).searchParams.get('resource_type')).toBe('network_device'));
    await userEvent.selectOptions(screen.getByLabelText('Estado administrativo'), 'maintenance');
    await waitFor(() => expect(new URL(String(fetchMock.mock.calls.at(-1)![0])).searchParams.get('administrative_state')).toBe('maintenance'));
    const params = new URL(String(fetchMock.mock.calls.at(-1)![0])).searchParams;
    expect(params.get('page')).toBe('1');
    expect([...params.keys()].sort()).toEqual(['administrative_state', 'page', 'per_page', 'resource_type']);
    expect(screen.queryByRole('searchbox')).not.toBeInTheDocument();
  });

  it('permite escolher dimensão de página até 100', async () => {
    const fetchMock = inventoryHttp(url => json(page([], { per_page: Number(url.searchParams.get('per_page')) })));
    renderApp();
    await screen.findByRole('heading', { name: 'Nenhum recurso encontrado' });
    await userEvent.selectOptions(screen.getByLabelText('Por página'), '100');
    await waitFor(() => expect(new URL(String(fetchMock.mock.calls.at(-1)![0])).searchParams.get('per_page')).toBe('100'));
  });

  it('mostra lista vazia sem inventar recursos', async () => {
    inventoryHttp(() => json(page([])));
    renderApp();
    await screen.findByRole('heading', { name: 'Nenhum recurso encontrado' });
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Seguinte' })).toBeDisabled();
  });

  it('mostra loading enquanto aguarda a listagem', async () => {
    let finish: ((value: Response) => void) | undefined;
    inventoryHttp(() => new Promise<Response>(resolve => { finish = resolve; }));
    renderApp();
    expect(await screen.findByText('A carregar os recursos…')).toBeInTheDocument();
    finish?.(json(page([])));
    await screen.findByRole('heading', { name: 'Nenhum recurso encontrado' });
  });

  it('limpa a sessão quando a API devolve 401', async () => {
    inventoryHttp(() => failure(401, 'unauthenticated'));
    renderApp();
    await screen.findByRole('heading', { name: 'Iniciar sessão' });
    expect(screen.getByRole('alert')).toHaveTextContent('sessão terminou');
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });

  it('mostra acesso negado para 403 sem inventar uma lista vazia', async () => {
    inventoryHttp(() => failure(403, 'forbidden'));
    renderApp();
    expect(await screen.findByRole('alert')).toHaveTextContent('Não tem permissão');
    expect(screen.queryByText('Nenhum recurso encontrado')).not.toBeInTheDocument();
  });

  it('trata falha de rede na listagem e repete só quando solicitado', async () => {
    let available = false;
    const fetchMock = inventoryHttp(() => available ? json(page()) : Promise.reject(new TypeError('network')));
    renderApp();
    expect(await screen.findByRole('alert')).toHaveTextContent('contactar o servidor');
    expect(fetchMock).toHaveBeenCalledTimes(3);
    available = true;
    await userEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }));
    await screen.findByRole('link', { name: /Router do laboratório/ });
    expect(fetchMock).toHaveBeenCalledTimes(4);
  });

  it.each([403, 404, 500])('detalhe trata HTTP %s', async status => {
    inventoryHttp(() => failure(status, status === 404 ? 'not_found' : 'forbidden'));
    renderApp('/inventory/' + resource.id);
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(status === 404 ? 'não encontrado' : status === 403 ? 'Não tem permissão' : 'indisponível');
    expect(screen.queryByText(resource.description!)).not.toBeInTheDocument();
    expect(screen.queryByText(/Texto interno/)).not.toBeInTheDocument();
  });

  it('mostra atributos, datas e valores ausentes sem interpretar HTML', async () => {
    inventoryHttp(() => json({ ...resource, description: '<script>não executar</script>',
      attributes: { note: '<img src=x onerror=alert(1)>', nested: { value: 5 } } }));
    renderApp('/inventory/' + resource.id);
    await screen.findByRole('heading', { name: resource.display_name });
    expect(screen.getByText('<script>não executar</script>')).toBeInTheDocument();
    expect(document.querySelector('main script')).toBeNull();
    expect(document.querySelector('main img')).toBeNull();
    expect(screen.getByText(/"nested"/)).toBeInTheDocument();
    expect(screen.getByText('Não disponível')).toBeInTheDocument();
    expect(screen.getByText('Criado em')).toBeInTheDocument();
  });

  it('recusa uma resposta de inventário incompatível', async () => {
    inventoryHttp(() => json({ items: [{}], total: 1, page: 1, per_page: 50 }));
    renderApp();
    expect(await screen.findByRole('alert')).toHaveTextContent('resposta incompatível');
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });

  it('mostra tipos desconhecidos como texto, mesmo com nomes de propriedades herdadas', async () => {
    inventoryHttp(() => json(page([{ ...resource, resource_type: 'constructor' }])));
    renderApp();
    expect(await screen.findByRole('cell', { name: 'constructor' })).toBeInTheDocument();
  });

  it('as áreas futuras não têm links operacionais', async () => {
    mockHttp();
    renderApp();
    await screen.findByRole('heading', { name: 'Inventário' });
    for (const label of ['Descoberta', 'Monitorização', 'Alertas', 'Administração']) {
      expect(screen.getByText(label)).toBeInTheDocument();
      expect(screen.queryByRole('link', { name: label })).not.toBeInTheDocument();
    }
    expect(screen.getAllByText('Em breve')).toHaveLength(4);
  });

  it('cancela a consulta anterior quando os filtros mudam', async () => {
    const signals: (AbortSignal | null | undefined)[] = [];
    inventoryHttp((url, options) => {
      signals.push(options.signal);
      if (url.searchParams.get('resource_type')) return json(page([]));
      return new Promise<Response>(() => {});
    });
    renderApp();
    await screen.findByText('A carregar os recursos…');
    await userEvent.selectOptions(screen.getByLabelText('Tipo de recurso'), 'service');
    await screen.findByRole('heading', { name: 'Nenhum recurso encontrado' });
    expect(signals[0]?.aborted).toBe(true);
  });
});
