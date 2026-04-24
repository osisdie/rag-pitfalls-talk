"use client";

/**
 * Thumbnail strip for bot responses. Pattern ported from
 * Agentory-CS — clickable thumbnails with onError local→external
 * fallback. Used by pit_10 (employee photos) and pit_19
 * (image materialization).
 */
export function ImageThumbnails({ urls }: { urls: string[] }) {
  if (!urls.length) return null;
  return (
    <div className="flex flex-wrap gap-2 mt-2">
      {urls.slice(0, 4).map((u, i) => (
        <a
          key={i}
          href={u}
          target="_blank"
          rel="noreferrer"
          className="block"
          title="open full-size"
        >
          <img
            src={u}
            alt={`thumb ${i + 1}`}
            className="w-24 h-24 rounded-lg border border-slate-700 object-cover hover:border-brand"
            onError={(e) => {
              // Broken image — swap to a tiny placeholder so the row
              // layout doesn't collapse. Pit_19 teaches exactly this.
              (e.target as HTMLImageElement).src =
                "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='96' height='96'><rect width='100%' height='100%' fill='%231e293b'/><text x='50%' y='50%' text-anchor='middle' fill='%23f87171' font-family='sans-serif' font-size='10'>broken</text></svg>";
            }}
          />
        </a>
      ))}
    </div>
  );
}
