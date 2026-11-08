import { act, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { failure, json, mockHttp, page, resource, user } from '../test/http';
import type { Handler } from '../test/http';
import { renderApp } from '../test/renderApp';

function editorHttp(handler: Handler) {
  return mockHttp((url, options) => {
    if (url.pathname.endsWith('/auth/me')) return json({ user: { ...user, roles: ['inventory_editor'] } });
    if (url.pathname.endsWith('/auth/csrf')) return json({ csrf_token: 'test-edit-csrf' });
    return handler(url, options);
  });
}

describe('criação e edição de recursos', () => {
  it('cria, mostra o detalhe persistido, edita com versão e apresenta a lista atualizada', async () => {
    let saved = { ...resource };
    const writes: RequestInit[] = [];
    editorHttp((url, options) => {
      if (['POST', 'PATCH'].includes(options.method || '')) {
        writes.push(options);
        const body = JSON.parse(String(options.body));
        expect(options.headers).toMatchObject({ 'X-CSRF-Token': 'test-edit-csrf' });
        expect(options.credentials).toBe('include');
        if (options.method === 'PATCH') expect(body.row_version).toBe(1);
        else expect(body).not.toHaveProperty('row_version');
        saved = { ...saved, ...body, row_version: writes.length };
        return json(saved, options.method === 'POST' ? 201 : 200);
      }
      return json(url.pathname.endsWith('/resources') ? page([saved]) : saved);
    });
    renderApp();
    await userEvent.click(await screen.findByRole('link', { name: 'Adicionar recurso' }));
    expect(screen.getByText(/Não são necessárias credenciais/)).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: 'Arquivado' })).not.toBeInTheDocument();
    await userEvent.type(screen.getByLabelText('Nome'), 'Novo recurso UI');
    await userEvent.selectOptions(screen.getByLabelText('Tipo de recurso'), 'service');
    await userEvent.type(screen.getByLabelText('Descrição'), 'Descrição inicial');
    await userEvent.selectOptions(screen.getByLabelText('Estado administrativo'), 'maintenance');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar recurso' }));
    await screen.findByRole('heading', { name: 'Novo recurso UI' });
    expect(screen.getByText('Descrição inicial')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('link', { name: 'Editar' }));
    expect(await screen.findByLabelText('Nome')).toHaveValue('Novo recurso UI');
    await userEvent.clear(screen.getByLabelText('Nome'));
    await userEvent.type(screen.getByLabelText('Nome'), 'Recurso UI editado');
    await userEvent.clear(screen.getByLabelText('Descrição'));
    await userEvent.selectOptions(screen.getByLabelText('Estado administrativo'), 'disabled');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar recurso' }));
    await screen.findByRole('heading', { name: 'Recurso UI editado' });
    expect(screen.getByText('Sem descrição.')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('link', { name: '← Voltar ao inventário' }));
    await screen.findByRole('link', { name: /Recurso UI editado/ });
    expect(screen.getByRole('cell', { name: 'Desativado' })).toBeInTheDocument();
    expect(writes).toHaveLength(2);
  });

  it('valida nome vazio sem enviar e permite cancelar', async () => {
    const http = editorHttp(() => json(page()));
    renderApp('/inventory/new');
    await userEvent.click(await screen.findByRole('button', { name: 'Guardar recurso' }));
    expect(screen.getByRole('alert')).toHaveTextContent('entre 1 e 255');
    expect(screen.getByLabelText('Nome')).toHaveAttribute('aria-invalid', 'true');
    expect(http.mock.calls.every(call => call[1]?.method === 'GET')).toBe(true);
    await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }));
    await screen.findByRole('heading', { name: 'Inventário' });
  });

  it('mantém todos os valores após erro de validação e permite corrigir', async () => {
    let writes = 0;
    editorHttp((_, options) => {
      if (options.method === 'POST') { writes++; return failure(400, 'invalid_request'); }
      return json(page());
    });
    renderApp('/inventory/new');
    await userEvent.type(await screen.findByLabelText('Nome'), 'Conservar nome');
    await userEvent.type(screen.getByLabelText('Descrição'), 'Conservar descrição');
    await userEvent.selectOptions(screen.getByLabelText('Tipo de recurso'), 'cluster');
    await userEvent.selectOptions(screen.getByLabelText('Estado administrativo'), 'maintenance');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar recurso' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Verifique os dados');
    expect(screen.getByLabelText('Nome')).toHaveValue('Conservar nome');
    expect(screen.getByLabelText('Descrição')).toHaveValue('Conservar descrição');
    expect(screen.getByLabelText('Tipo de recurso')).toHaveValue('cluster');
    expect(screen.getByLabelText('Estado administrativo')).toHaveValue('maintenance');
    expect(screen.getByRole('button', { name: 'Guardar recurso' })).toBeEnabled();
    expect(writes).toBe(1);
  });

  it('impede submissões duplicadas durante a gravação', async () => {
    let finish!: (value: Response) => void;
    let writes = 0;
    editorHttp((_, options) => {
      if (options.method === 'POST') { writes++; return new Promise<Response>(resolve => { finish = resolve; }); }
      return json(resource);
    });
    renderApp('/inventory/new');
    await userEvent.type(await screen.findByLabelText('Nome'), 'Uma única gravação');
    await userEvent.dblClick(screen.getByRole('button', { name: 'Guardar recurso' }));
    expect(screen.getByRole('button', { name: 'A guardar…' })).toBeDisabled();
    expect(screen.getByLabelText('Nome')).toBeDisabled();
    expect(writes).toBe(1);
    await act(async () => { finish(json(resource, 201)); });
    await screen.findByRole('heading', { name: resource.display_name });
  });

  it('conflito conserva o rascunho, bloqueia nova gravação e permite consultar a versão atual', async () => {
    let writes = 0;
    editorHttp((_, options) => {
      if (options.method === 'PATCH') { writes++; return failure(409, 'version_conflict'); }
      return json({ ...resource, row_version: writes ? 2 : 1 });
    });
    renderApp('/inventory/' + resource.id + '/edit');
    await userEvent.clear(await screen.findByLabelText('Nome'));
    await userEvent.type(screen.getByLabelText('Nome'), 'O meu rascunho');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar recurso' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('alterado entretanto');
    expect(screen.getByLabelText('Nome')).toHaveValue('O meu rascunho');
    expect(screen.getByRole('button', { name: 'Guardar recurso' })).toBeDisabled();
    await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }));
    await screen.findByRole('heading', { name: resource.display_name });
    expect(writes).toBe(1);
  });

  it('não repete uma criação de resultado incerto', async () => {
    let writes = 0;
    editorHttp((_, options) => {
      if (options.method === 'POST') { writes++; return Promise.reject(new TypeError('network')); }
      return json(page());
    });
    renderApp('/inventory/new');
    await userEvent.type(await screen.findByLabelText('Nome'), 'Resultado incerto');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar recurso' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('confirmar o resultado');
    expect(screen.getByLabelText('Nome')).toHaveValue('Resultado incerto');
    expect(screen.getByRole('button', { name: 'Guardar recurso' })).toBeDisabled();
    expect(writes).toBe(1);
  });

  it('reader não vê ações de escrita nem acede ao formulário por URL', async () => {
    mockHttp();
    const view = renderApp();
    await screen.findByRole('link', { name: /Router do laboratório/ });
    expect(screen.queryByRole('link', { name: 'Adicionar recurso' })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('link', { name: /Router do laboratório/ }));
    await screen.findByRole('heading', { name: resource.display_name });
    expect(screen.queryByRole('link', { name: 'Editar' })).not.toBeInTheDocument();
    view.unmount();
    renderApp('/inventory/' + resource.id + '/edit');
    expect(await screen.findByRole('alert')).toHaveTextContent('Não tem permissão');
    expect(screen.queryByLabelText('Nome')).not.toBeInTheDocument();
  });

  it('expira a sessão se a gravação devolver 401', async () => {
    editorHttp(() => failure(401, 'unauthenticated'));
    renderApp('/inventory/new');
    await userEvent.type(await screen.findByLabelText('Nome'), 'Sessão terminada');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar recurso' }));
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Iniciar sessão' })).toBeInTheDocument());
  });

  it('preserva os valores se o backend retirar a permissão durante a edição', async () => {
    editorHttp((_, options) => options.method === 'PATCH' ? failure(403, 'forbidden') : json(resource));
    renderApp('/inventory/' + resource.id + '/edit');
    await userEvent.clear(await screen.findByLabelText('Nome'));
    await userEvent.type(screen.getByLabelText('Nome'), 'Valores preservados');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar recurso' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Não tem permissão');
    expect(screen.getByLabelText('Nome')).toHaveValue('Valores preservados');
    expect(screen.queryByText('Texto interno')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Cancelar' })).toBeEnabled();
  });

  it('não disponibiliza edição de um recurso arquivado por URL', async () => {
    editorHttp(() => json({ ...resource, administrative_state: 'archived' }));
    renderApp('/inventory/' + resource.id + '/edit');
    expect(await screen.findByRole('alert')).toHaveTextContent('arquivado');
    expect(screen.queryByRole('button', { name: 'Guardar recurso' })).not.toBeInTheDocument();
  });
});
