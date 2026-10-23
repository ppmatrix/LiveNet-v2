export function Loading({ label = 'A carregar…' }: { label?: string }) {
  return <div className="feedback" role="status"><span className="spinner" aria-hidden="true" />{label}</div>;
}

export function ErrorNotice({ message, retry }: { message: string; retry?: () => void }) {
  return <div className="notice notice-error" role="alert">
    <p>{message}</p>
    {retry && <button className="button button-secondary" onClick={retry}>Tentar novamente</button>}
  </div>;
}
