import { useCallback, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { useNavigate, useParams } from 'react-router';
import { ApiError, errorMessage } from '../api/client';
import { administrativeStates, resourceTypes } from '../api/contracts';
import type { Resource } from '../api/contracts';
import { createResource, getResource, updateResource } from '../api/inventory';
import { useRemote } from '../api/useRemote';
import { useSession } from '../auth/SessionProvider';
import { ErrorNotice, Loading } from '../components/Feedback';

function ResourceForm({ resource }: { resource?: Resource }) {
  const navigate = useNavigate();
  const { expire } = useSession();
  const [name, setName] = useState(resource?.display_name || '');
  const [type, setType] = useState(resource?.resource_type || 'virtual_machine');
  const [description, setDescription] = useState(resource?.description || '');
  const [state, setState] = useState(resource?.administrative_state || 'active');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [nameError, setNameError] = useState(false);
  const [blocked, setBlocked] = useState(false);
  const busy = useRef(false);
  const cancelTo = resource ? '/inventory/' + encodeURIComponent(resource.id) : '/inventory';

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy.current || blocked) return;
    const invalidName = !name.trim() || name.trim().length > 255;
    setNameError(invalidName);
    if (invalidName) return;
    busy.current = true;
    setPending(true);
    setError(null);
    try {
      const data = { display_name: name.trim(), resource_type: type,
        description: description || null, administrative_state: state };
      const saved = resource ? await updateResource(resource.id, data, resource.row_version) : await createResource(data);
      navigate('/inventory/' + encodeURIComponent(saved.id));
    } catch (failure) {
      if (failure instanceof ApiError && failure.status === 401) { expire(); return; }
      const uncertain = !(failure instanceof ApiError) || failure.status === 0 || failure.status >= 500;
      setBlocked(uncertain || (failure instanceof ApiError && failure.status === 409));
      setError(uncertain
        ? 'Não foi possível confirmar o resultado. Os seus valores foram mantidos. Cancele e consulte o inventário antes de repetir a operação.'
        : errorMessage(failure));
    } finally { busy.current = false; setPending(false); }
  }

  return <>
    <div className="page-heading"><div><p className="eyebrow">INVENTORY</p>
      <h1>{resource ? 'Editar recurso' : 'Adicionar recurso'}</h1>
      <p className="muted">Registe informação administrativa. Não são necessárias credenciais do equipamento.</p></div></div>
    <section className="surface detail-panel resource-form">
      {error && <ErrorNotice message={error} />}
      <form onSubmit={submit} noValidate aria-busy={pending}>
        <fieldset disabled={pending}>
          <legend className="sr-only">Dados do recurso</legend>
          <div><label htmlFor="resource-name">Nome</label>
            <input id="resource-name" value={name} onChange={event => setName(event.target.value)} required maxLength={255}
              aria-invalid={nameError} aria-describedby={nameError ? 'resource-name-error' : undefined} />
            {nameError && <p className="field-error" id="resource-name-error" role="alert">Indique um nome entre 1 e 255 caracteres.</p>}</div>
          <div><label htmlFor="resource-form-type">Tipo de recurso</label>
            <select id="resource-form-type" value={type} onChange={event => setType(event.target.value)} required>
              {Object.entries(resourceTypes).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select></div>
          <div><label htmlFor="resource-description">Descrição</label>
            <textarea id="resource-description" value={description} onChange={event => setDescription(event.target.value)} rows={4} /></div>
          <div><label htmlFor="resource-form-state">Estado administrativo</label>
            <select id="resource-form-state" value={state} onChange={event => setState(event.target.value)} required aria-describedby="administrative-state-help">
              {Object.entries(administrativeStates).filter(([value]) => value !== 'archived')
                .map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
            <p className="context-note" id="administrative-state-help">O estado administrativo não indica a disponibilidade operacional do recurso.</p></div>
        </fieldset>
        <div className="page-actions"><button className="button" type="submit" disabled={pending || blocked}>{pending ? 'A guardar…' : 'Guardar recurso'}</button>
          <button className="button button-secondary" type="button" disabled={pending} onClick={() => navigate(cancelTo)}>Cancelar</button></div>
      </form>
    </section>
  </>;
}

export function ResourceCreatePage() {
  const { session } = useSession();
  if (!session.user?.roles.includes('inventory_editor')) return <ErrorNotice message="Não tem permissão para editar recursos." />;
  return <ResourceForm />;
}

function EditableResource({ id }: { id: string }) {
  const load = useCallback((signal: AbortSignal) => getResource(id, signal), [id]);
  const { result, retry } = useRemote(load);
  if (result.status === 'loading') return <Loading label="A carregar o recurso…" />;
  if (result.status === 'error') return <ErrorNotice message={errorMessage(result.error)}
    retry={result.error instanceof ApiError && [403, 404].includes(result.error.status) ? undefined : retry} />;
  if (result.data.archived_at || result.data.administrative_state === 'archived') return <ErrorNotice message="Este recurso está arquivado e não pode ser editado." />;
  return <ResourceForm key={result.data.id} resource={result.data} />;
}

export function ResourceEditPage() {
  const { resourceId = '' } = useParams();
  const { session } = useSession();
  if (!session.user?.roles.includes('inventory_editor')) return <ErrorNotice message="Não tem permissão para editar recursos." />;
  return <EditableResource key={resourceId} id={resourceId} />;
}
