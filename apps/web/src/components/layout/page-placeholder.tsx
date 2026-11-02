type PagePlaceholderProps = {
  title: string;
  description: string;
  arrivesIn: string;
};

/** Marks a screen that is not built yet. Removed as each phase is finished. */
export function PagePlaceholder({ title, description, arrivesIn }: PagePlaceholderProps) {
  return (
    <section>
      <h1 className="text-3xl font-bold">{title}</h1>
      <p className="mt-1 text-muted">{description}</p>
      <div className="mt-6 rounded-card border border-border bg-surface p-8 shadow-card">
        <p className="text-muted">This screen arrives in {arrivesIn}.</p>
      </div>
    </section>
  );
}
