import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="mx-auto max-w-lg px-6 py-24 text-center">
      <div className="font-mono text-4xl font-semibold text-content-primary">
        404
      </div>
      <p className="mt-2 font-mono text-sm text-content-muted">
        no route here
      </p>
      <Link to="/" className="btn btn-primary mt-6 inline-flex">
        Back to control plane
      </Link>
    </div>
  );
}
